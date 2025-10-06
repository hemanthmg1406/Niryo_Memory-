
MEAN_DOG_A = [0.12, 0.45, 0.98, ...] 
MEAN_CAT_B = [0.99, 0.05, 0.11, ...] 
MEAN_CAR_C = [0.55, 0.60, 0.70, ...] 

# --- MASTER DATA DICTIONARY ---
CARD_CATEGORY_DATA = {
    "Dog": {
        "audio": "i_found_a_dog.mp3", 
        "mean_vec": MEAN_DOG_A, 
        "sentence": "Oh, I found a Dog! Now I need to search for the other Dog."
    },
    "Cat": {
        "audio": "i_found_a_cat.mp3", 
        "mean_vec": MEAN_CAT_B, 
        "sentence": "Oh, I found a Cat! Now I need to search for the other Cat."
    },
    "Car": {
        "audio": "i_found_a_car.mp3", 
        "mean_vec": MEAN_CAR_C, 
        "sentence": "Oh, I found a Car! Now I need to search for the other Car."
    },
    # ... (Add all 10 card categories)
}

# Threshold for card identification confidence
IDENTIFICATION_DISTANCE_THRESHOLD = 0.08