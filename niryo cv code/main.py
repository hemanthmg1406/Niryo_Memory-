import cv2
import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from sklearn.decomposition import PCA
import json
import os
import time

# --- Model Setup ---
resnet = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
resnet.fc = torch.nn.Identity()
resnet.eval()

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

features = []
labels = []
coords_3d = []
id_counter = 0

def auto_crop_inside_white_edges(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    thresh_inv = cv2.bitwise_not(thresh)
    contours, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image
    card_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(card_contour)
    roi = image[y:y+h, x:x+w]
    roi_gray = gray[y:y+h, x:x+w]

    def find_border_index(arr, direction='left', threshold=240, margin=5):
        if direction == 'left':
            for i in range(arr.shape[1]):
                if np.mean(arr[:, i]) < threshold:
                    return max(i - margin, 0)
            return 0
        if direction == 'right':
            for i in reversed(range(arr.shape[1])):
                if np.mean(arr[:, i]) < threshold:
                    return min(i + margin, arr.shape[1])
            return arr.shape[1]
        if direction == 'top':
            for i in range(arr.shape[0]):
                if np.mean(arr[i, :]) < threshold:
                    return max(i - margin, 0)
            return 0
        if direction == 'bottom':
            for i in reversed(range(arr.shape[0])):
                if np.mean(arr[i, :]) < threshold:
                    return min(i + margin, arr.shape[0])
            return arr.shape[0]

    left = find_border_index(roi_gray, 'left')
    right = find_border_index(roi_gray, 'right')
    top = find_border_index(roi_gray, 'top')
    bottom = find_border_index(roi_gray, 'bottom')

    cropped = roi[top:bottom, left:right]
    return cropped

# --- Capture and Process Loop ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Cannot access camera")
    exit()

print("📷 Automatically scanning for single card...")

detection_time = None
wait_after_capture = False
capture_done = False
next_allowed_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    bright = cv2.convertScaleAbs(frame, alpha=1.3, beta=30)
    gray = cv2.cvtColor(bright, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    current_time = time.time()

    if hierarchy is not None and current_time >= next_allowed_time:
        hierarchy = hierarchy[0]
        card_found = False
        for i, cnt in enumerate(contours):
            if hierarchy[i][3] == -1 and cv2.contourArea(cnt) > 1000:
                if not detection_time:
                    print("🃏 Card detected. Waiting 2 seconds to capture...")
                    detection_time = current_time
                elif current_time - detection_time >= 2:
                    print("📸 Capturing frame...")
                    freeze_frame = frame.copy()
                    x, y, w, h = cv2.boundingRect(cnt)
                    scanned_card = freeze_frame[y:y+h, x:x+w]
                    card = auto_crop_inside_white_edges(scanned_card)
                    card_name = f"card_{id_counter+1}.jpg"
                    cv2.imwrite(card_name, card)

                    img = Image.fromarray(cv2.cvtColor(card, cv2.COLOR_BGR2RGB))
                    tensor = transform(img).unsqueeze(0)
                    with torch.no_grad():
                        vec = resnet(tensor).squeeze().numpy()

                    if not np.any(vec):
                        print("⚠️ Skipped zero vector")
                        detection_time = None
                        continue

                    features.append(vec.tolist())
                    labels.append(card_name)
                    id_counter += 1
                    print(f"✅ Saved {card_name}")
                    card_found = True
                    detection_time = None
                    next_allowed_time = current_time + 5  # wait before next scan
                    break
                break
        else:
            detection_time = None

    if features:
        n_components = min(3, len(features))
        try:
            proj = PCA(n_components=n_components)
            vec_array = np.array(features)
            coords = proj.fit_transform(vec_array)
            if n_components < 3:
                coords = np.pad(coords, ((0, 0), (0, 3 - n_components)), 'constant')
            coords_3d = coords.tolist()
        except Exception as e:
            print("❌ Projection failed:", e)
            continue

        def compute_similarity_groups(features, threshold=10):
            group_labels = [-1] * len(features)
            group_id = 0
            for i in range(len(features)):
                if group_labels[i] == -1:
                    group_labels[i] = group_id
                    for j in range(i + 1, len(features)):
                        dist = np.linalg.norm(np.array(features[i]) - np.array(features[j]))
                        if dist < threshold:
                            group_labels[j] = group_id
                    group_id += 1
            return group_labels

        groups = compute_similarity_groups(features)

        nodes = [{"id": i, "label": labels[i], "group": groups[i],
                  "x": coords_3d[i][0], "y": coords_3d[i][1], "z": coords_3d[i][2]} for i in range(len(coords_3d))]

        links = []
        for i in range(len(coords_3d)):
            for j in range(i + 1, len(coords_3d)):
                dist = np.linalg.norm(np.array(coords_3d[i]) - np.array(coords_3d[j]))
                links.append({"source": i, "target": j, "distance": round(dist, 2)})

        with open("graph_data.json", "w") as f:
            json.dump({"nodes": nodes, "links": links}, f, indent=2)

    cv2.imshow("Card Scanner", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("👋 Exiting")
        break

cap.release()
cv2.destroyAllWindows()
