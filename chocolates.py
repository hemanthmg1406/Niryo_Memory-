from pyniryo2 import NiryoRobot
import time
import os
import random
import pygame

# --- Robot Configuration ---
ROBOT_IP_ADDRESS = "169.254.200.200"
STABLE_WAIT_TIME = 1.0
GRIPPER_TOOL_ID = 1  # Vacuum or gripper tool ID

# --- Pose Definitions ---
HOME_POSE = [0.22, -0.0, 0.21, -2.96, 1.54, -2.9783]
PRE_GRASP_POSE = [0.26, 0.03, 0.15, 1.55, 0.2, 1.497]
GIVE_POSE = [0.41, 0.0, 0.25, -0.03, 1.06, -0.0264]

# --- Visual & Audio ---
CHOCOLATE_BROWN_COLOR = [139, 69, 19]
SOUND_FOLDER = "sounds/chocolate/"

# --- Initialize robot and sound ---
robot = NiryoRobot(ROBOT_IP_ADDRESS)


pygame.mixer.init()

def play_random_chocolate_sound():
    """Play a random chocolate-themed sound."""
    files = [f for f in os.listdir(SOUND_FOLDER) if f.endswith(".mp3") or f.endswith(".wav")]
    if not files:
        print("No sound files found in:", SOUND_FOLDER)
        return
    file_path = os.path.join(SOUND_FOLDER, random.choice(files))
    print(f"Playing sound: {file_path}")
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()

# --- Chocolate Giving Routine ---
try:
    print("Moving to home pose...")
    robot.arm.move_pose(HOME_POSE)

    print("Approaching grasp position...")
    robot.arm.move_pose(PRE_GRASP_POSE)
    time.sleep(STABLE_WAIT_TIME)

    print("Grasping chocolate...")
    robot.tool.grasp_with_tool()
    time.sleep(1.0)

    print("Moving to give position...")
    robot.arm.move_pose(GIVE_POSE)

    print("Running LED chase effect and playing sound...")
    robot.led_ring.chase(CHOCOLATE_BROWN_COLOR, 3)  # 3 = chase speed
    play_random_chocolate_sound()

    time.sleep(2.5)  # Wait until sound/LED finishes

    print("Releasing chocolate...")
    robot.tool.release_with_tool()

    print("Returning to home pose...")
    robot.arm.move_pose(HOME_POSE)

    print("Sequence complete.")

finally:
    robot.led_ring.turn_off()
    #robot.close_connection()
