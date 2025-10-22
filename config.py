ROBOT_IP_ADDRESS = "169.254.200.200"
STABLE_WAIT_TIME = 1.0  # Seconds card must remain stable for scan
GRIPPER_TOOL_ID  = 1    # ID for the vacuum gripper (or custom tool)

# --- GAME BOARD LAYOUT ---
ROWS, COLS       = 4, 5
ALL_SQUARE_IDS   = [r + c for r in "ABCD" for c in "12345"]
# CARD_BOX defines the region of interest (ROI) in the camera feed (x, y, w, h)
CARD_BOX         = (270, 190, 190, 190)  

# --- COMPUTER VISION CONFIG ---
PCA_DIMS                  = 3
# Note: These values can be changed later to adjust difficulty
MATCH_DISTANCE_THRESHOLD  = 75  # Max distance for PCA to count as match
MATCH_KNN_SCORE_THRESHOLD = 0.5  # Min score for KNN to count as match

# --- DIFFICULTY CONFIG ---
DIFFICULTY_DEFAULT = "hard" # Default setting when the game starts

SOUND_FOLDER = "sounds/chocolate/"

# --- Robot Pose Definitions (Joint Angles) ---
# Each list represents the angles for the 6 joints of the robot.
HOME_POSE = [0.13, 0.21, 0.12, 2.63, 1.49, -2.8043]
PRE_GRASP_POSE = [0.13, 0.21, 0.07, 2.63, 1.49, -2.8043]
GIVE_POSE = [0.41, 0.0, 0.25, -0.03, 1.06, -0.0264]

# --- Visual & Tool Configuration ---
# An RGB color value for the LED ring animation (a nice chocolatey brown)
CHOCOLATE_BROWN_COLOR = [139, 69, 19]