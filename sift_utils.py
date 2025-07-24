import cv2
import numpy as np

# -------- Global SIFT Detector and Matcher --------

sift = cv2.SIFT_create()
bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

# ----------- Feature Extraction ------------

def extract_sift_signature(image):
    """
    Extracts SIFT keypoints and descriptors from an image.
    Returns:
        mean vector (128D), raw descriptors
        or (None, None) if not enough features.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    kp, desc = sift.detectAndCompute(gray, None)

    if desc is None or len(desc) == 0:
        return None, None

    mean_vec = np.mean(desc, axis=0)
    return mean_vec, desc

# ----------- KNN Matching Score ------------

def compute_knn_match_score(desc1, desc2, ratio_thresh=0.75):
    """
    Computes the KNN Lowe-ratio matching score between two descriptors.
    Returns match ratio: good_matches / min(len(desc1), len(desc2))
    """
    if desc1 is None or desc2 is None:
        return 0.0

    matches = bf.knnMatch(desc1, desc2, k=2)
    good = []

    for m_n in matches:
        if len(m_n) < 2:
            continue
        m, n = m_n
        if m.distance < ratio_thresh * n.distance:
            good.append(m)

    return len(good) / min(len(desc1), len(desc2))

# ----------- Auto-Cropping Inside White Edges ------------

def auto_crop_inside_white_edges(image, white_thresh=240, margin=5):
    """
    Crops inside white border of a card.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    inv = cv2.bitwise_not(thresh) #invert binary image
    contours, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return image

    cnt = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(cnt)
    roi = image[y:y+h, x:x+w]
    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    def border_idx(arr, dir):
        if dir == 'left':
            for i in range(arr.shape[1]):
                if np.mean(arr[:, i]) < white_thresh:
                    return max(i - margin, 0)
            return 0
        if dir == 'right':
            for i in reversed(range(arr.shape[1])):
                if np.mean(arr[:, i]) < white_thresh:
                    return min(i + margin, arr.shape[1])
            return arr.shape[1]
        if dir == 'top':
            for i in range(arr.shape[0]):
                if np.mean(arr[i, :]) < white_thresh:
                    return max(i - margin, 0)
            return 0
        if dir == 'bottom':
            for i in reversed(range(arr.shape[0])):
                if np.mean(arr[i, :]) < white_thresh:
                    return min(i + margin, arr.shape[0])
            return arr.shape[0]

    l = border_idx(roi_gray, 'left')
    r = border_idx(roi_gray, 'right')
    t = border_idx(roi_gray, 'top')
    b = border_idx(roi_gray, 'bottom')
    return roi[t:b, l:r]

# ----------- Bounding Box Drawing ------------

def draw_oriented_bounding_box(img):
    """
    Draws a green box around the largest white object.
    """
    bright = cv2.convertScaleAbs(img, alpha=1.3, beta=30) #contast,brightness
    gray = cv2.cvtColor(bright, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    box = None
    if hierarchy is not None:
        for i, cnt in enumerate(contours):
            if hierarchy[0][i][3] == -1 and cv2.contourArea(cnt) > 1000:
                rect = cv2.minAreaRect(cnt)
                pts = cv2.boxPoints(rect)
                box = pts.astype(np.intp)
                cv2.drawContours(img, [box], 0, (0, 255, 0), 2)
                break

    return img, box

def mask_outside_card(image, box1):
    """
    Masks everything except the specified rectangular box.
    """
    mask = np.zeros_like(image)
    x, y, w, h = box1
    mask[y:y+h, x:x+w] = image[y:y+h, x:x+w]
    return mask
