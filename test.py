# prototype_norms_generator.py
# Computes L2-norms of mean SIFT descriptors for a set of labeled prototype images

import cv2
import numpy as np
import os
import json

# List of prototype filenames and their semantic class names
prototypes = {
    'flower.jpg':     'flower',
    'cat.jpg':        'cat',
    'icecream.jpg':   'ice_cream',
    'apple.jpg':      'apple',
    'strawberry.jpg': 'strawberry',
    'clock.jpg':      'clock',
    'torch.jpg':      'torch',
    'joker.jpg':      'joker',
    'ghost.jpg':      'ghost',
    'frog.jpg':       'frog'
}

# Initialize SIFT detector
sift = cv2.SIFT_create()

# Dictionary to hold computed norms
prototype_norms = {}

# Process each prototype image
for filename, label in prototypes.items():
    path = os.path.join(os.getcwd(), filename)
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Error: Could not load image '{filename}'")
        continue

    # Detect keypoints and compute descriptors
    keypoints, descriptors = sift.detectAndCompute(img, None)
    if descriptors is None or descriptors.size == 0:
        print(f"Warning: No descriptors found in '{filename}', skipping.")
        continue

    # Compute mean descriptor and its L2 norm
    mean_descriptor = descriptors.mean(axis=0)
    norm_value = float(np.linalg.norm(mean_descriptor))
    prototype_norms[label] = norm_value
    print(f"{label}: {len(keypoints)} keypoints, norm = {norm_value:.2f}")

# Save the mapping to JSON for later use
out_file = 'prototype_norms.json'
with open(out_file, 'w') as f:
    json.dump(prototype_norms, f, indent=2)

print(f"Prototype norms saved to '{out_file}'")
