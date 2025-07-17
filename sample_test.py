
import cv2
import numpy as np
import os
import json
import time
import csv
from sklearn.decomposition import PCA
import warnings

# --- SIFT + PCA Card Scanner with Match-Count Verification and CSV Export ---
# Captures cards via webcam, crops them,
# extracts mean SIFT-descriptors (128D), reduces to 3D via PCA,
# computes a tight clustering threshold (25th percentile of distances),
# verifies similarity with raw SIFT match-score,
# assigns groups, writes graph_data.json, and exports pairwise distances to CSV (once per pair).

# Initialize SIFT detector and BF matcher
sift = cv2.SIFT_create()
bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

# Parameters
stable_wait     = 2.0   # seconds box stability before capture
next_wait       = 5.0   # seconds between captures
max_pca_dims    = 3     # dimensions for force-graph
match_threshold = 0.3   # normalized match-count threshold
cluster_pct     = 50    # percentile for PCA-distance threshold

distances_csv = 'pairwise_distances.csv'
written_pairs = set()  # track which pairs have been written

# Data storage
features   = []      # list of 128-D mean descriptors
labels     = []      # corresponding card filenames
desc_list  = []      # raw SIFT descriptor arrays per card
coords_3d  = []      # PCA-reduced coordinates
id_counter = 0

# --- Utility Functions ---

def auto_crop_inside_white_edges(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    inv = cv2.bitwise_not(thresh)
    contours, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image
    cnt = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(cnt)
    roi = image[y:y+h, x:x+w]
    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    def border_idx(arr, dir, thresh=240, margin=5):
        if dir == 'left':
            for i in range(arr.shape[1]):
                if np.mean(arr[:, i]) < thresh:
                    return max(i-margin, 0)
            return 0
        if dir == 'right':
            for i in reversed(range(arr.shape[1])):
                if np.mean(arr[:, i]) < thresh:
                    return min(i+margin, arr.shape[1])
            return arr.shape[1]
        if dir == 'top':
            for i in range(arr.shape[0]):
                if np.mean(arr[i, :]) < thresh:
                    return max(i-margin, 0)
            return 0
        if dir == 'bottom':
            for i in reversed(range(arr.shape[0])):
                if np.mean(arr[i, :]) < thresh:
                    return min(i+margin, arr.shape[0])
            return arr.shape[0]

    l = border_idx(roi_gray, 'left')
    r = border_idx(roi_gray, 'right')
    t = border_idx(roi_gray, 'top')
    b = border_idx(roi_gray, 'bottom')
    return roi[t:b, l:r]


def draw_oriented_bounding_box(img):
    bright = cv2.convertScaleAbs(img, alpha=1.3, beta=30)
    gray   = cv2.cvtColor(bright, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    box = None
    if hierarchy is not None:
        for i, cnt in enumerate(contours):
            if hierarchy[0][i][3] == -1 and cv2.contourArea(cnt) > 1000:
                rect = cv2.minAreaRect(cnt)
                pts = cv2.boxPoints(rect)
                box = pts.astype(np.intp)
                cv2.drawContours(img, [box], 0, (0,255,0), 2)
                break
    return img, box


def compute_similarity_groups(coords, threshold, descs):
    """Clusters cards: PCA-dist <= threshold AND match_score >= match_threshold."""
    n = len(coords)
    grp_labels = [-1]*n
    gid = 0
    for i in range(n):
        if grp_labels[i] != -1: continue
        grp_labels[i] = gid
        for j in range(i+1, n):
            if grp_labels[j] == -1:
                d = np.linalg.norm(np.array(coords[i]) - np.array(coords[j]))
                if d <= threshold:
                    des1, des2 = descs[i], descs[j]
                    raw = bf.knnMatch(des1, des2, k=2)
                    good = []
                    for m_n in raw:
                        if len(m_n) < 2: continue
                        m, n2 = m_n
                        if m.distance < 0.75 * n2.distance:
                            good.append(m)
                    score = len(good) / min(len(des1), len(des2))
                    if score >= match_threshold:
                        grp_labels[j] = gid
        gid += 1
    return grp_labels

# Initialize CSV file with headers
with open(distances_csv, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Card A','Card B','PCA Distance'])

# --- Main Loop ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot access camera")
    exit()

print("Starting card scanning...")
last_center = None
stable_since = None
next_allowed = 0

detection_time = None
while True:
    ret, frame = cap.read()
    if not ret: continue
    disp, box = draw_oriented_bounding_box(frame.copy())
    cv2.imshow("Scanner", disp)
    t = time.time()

    if box is not None and t >= next_allowed:
        center = tuple(np.mean(box, axis=0).astype(int))
        if last_center is not None and np.linalg.norm(np.array(center)-np.array(last_center))<10:
            if stable_since is None: stable_since = t
            elif detection_time is None and (t - stable_since) >= stable_wait:
                detection_time = t
        else:
            stable_since = None
        last_center = center

        if detection_time and (t - detection_time) >= 1:
            snap = frame.copy()
            pts = box.astype('float32')
            w = int(max(np.linalg.norm(pts[0]-pts[1]), np.linalg.norm(pts[2]-pts[3])))
            h = int(max(np.linalg.norm(pts[1]-pts[2]), np.linalg.norm(pts[3]-pts[0])))
            dst = np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]], dtype='float32')
            M = cv2.getPerspectiveTransform(pts, dst)
            card = cv2.warpPerspective(snap, M, (w,h))
            card = auto_crop_inside_white_edges(card)

            gray = cv2.cvtColor(card, cv2.COLOR_BGR2GRAY)
            kp, des = sift.detectAndCompute(gray, None)
            if des is None or len(des)==0:
                print("No features, skipping.")
            else:
                mean_vec = des.mean(axis=0)
                features.append(mean_vec.tolist())
                desc_list.append(des)
                fname = f"card_{id_counter+1}.jpg"
                labels.append(fname)
                cv2.imwrite(fname, card)
                print(f"Saved {fname} with {len(kp)} keypoints.")
                id_counter += 1

            detection_time = None
            stable_since = None
            next_allowed = t + next_wait

    if len(features) >= 2:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
        arr = np.array(features)
        n_comp = min(max_pca_dims, arr.shape[0])
        pca = PCA(n_components=n_comp)
        pcs = pca.fit_transform(arr)
        if n_comp < 3:
            pcs = np.pad(pcs, ((0,0),(0,3-n_comp)), mode='constant')
        coords_3d = pcs.tolist()

        # Pairwise distances and CSV export (write each pair once)
        print("Pairwise distances in PCA space:")
        with open(distances_csv, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for i in range(len(coords_3d)):
                for j in range(i+1, len(coords_3d)):
                    pair = (labels[i], labels[j])
                    if pair not in written_pairs:
                        d = np.linalg.norm(np.array(coords_3d[i]) - np.array(coords_3d[j]))
                        print(f"  {labels[i]} vs {labels[j]}: {d:.2f}")
                        writer.writerow([labels[i], labels[j], f"{d:.2f}"])
                        written_pairs.add(pair)

        # Tight threshold from percentile
        dists = [np.linalg.norm(np.array(coords_3d[i]) - np.array(coords_3d[j]))
                 for i in range(len(coords_3d)) for j in range(i+1, len(coords_3d))]
        threshold = float(np.percentile(dists, cluster_pct)) if dists else 0.0

        groups = compute_similarity_groups(coords_3d, threshold, desc_list)

        # build JSON
        nodes, links = [], []
        for i, (x,y,z) in enumerate(coords_3d):
            nodes.append({"id": i, "label": labels[i], "group": groups[i], "x": x, "y": y, "z": z})
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                if groups[i] == groups[j]:
                    dist = round(np.linalg.norm(np.array(coords_3d[i]) - np.array(coords_3d[j])), 2)
                    links.append({"source": i, "target": j, "distance": dist})
        with open("graph_data.json", "w") as f:
            json.dump({"nodes": nodes, "links": links}, f, indent=2)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
