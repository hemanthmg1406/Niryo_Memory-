ROBOT_IP_ADDRESS = "169.254.200.200"
STABLE_WAIT_TIME = 2.0  # Seconds card must remain stable for scan
GRIPPER_TOOL_ID  = 1    # ID for the vacuum gripper (or custom tool)

# --- GAME BOARD LAYOUT ---
ROWS, COLS       = 4, 5
ALL_SQUARE_IDS   = [r + c for r in "ABCD" for c in "12345"]
# CARD_BOX defines the region of interest (ROI) in the camera feed (x, y, w, h)
CARD_BOX         = (190, 105, 270, 270)  

# --- COMPUTER VISION CONFIG ---
PCA_DIMS                  = 3
# Note: These values can be changed later to adjust difficulty
MATCH_DISTANCE_THRESHOLD  = 0.4  # Max distance for PCA to count as match
MATCH_KNN_SCORE_THRESHOLD = 0.5  # Min score for KNN to count as match

# --- DIFFICULTY CONFIG ---
DIFFICULTY_DEFAULT = "hard" # Default setting when the game starts