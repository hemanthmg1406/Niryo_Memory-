import cv2
import os
import time
from memory_queues import square_queue, gui_queue
from memory_logic import register_card
from sift_utils import extract_sift_signature, auto_crop_inside_white_edges, draw_oriented_bounding_box
from recorded_positions import *
from pyniryo2 import *
import pyniryo
from matplotlib import pyplot as plt
import numpy as np

robot_ip_address = "169.254.200.200"

robot = NiryoRobot(robot_ip_address)
robot.arm.calibrate_auto()
# robot.activate_vacuum()
robot.tool.release_with_tool()
robot.tool.grasp_with_tool()
robot.arm.move_pose(home_pose)

image_save_dir = "scanned_cards"
os.makedirs(image_save_dir, exist_ok=True)
ros_instance = NiryoRos("169.254.200.200")
vision = Vision(ros_instance)

def scan_all_cards():
    """
    For each square A1…D5:
      1) Go HOME → camera position → suction on
      2) Return HOME → square position → suction off
      3) Return HOME
    """
    for sq, drop_pose in pick_positions.items():
        # Go to camera position and grasp
        robot.arm.move_pose(home_pose)
        robot.arm.move_pose(card_position)
        robot.tool.grasp_with_tool()
        print(f"[SCAN_ALL] Suction on at camera for {sq}")

        # Go back home then to square and release
        robot.arm.move_pose(home_pose)
        robot.arm.move_pose(drop_pose)
        robot.tool.release_with_tool()
        print(f"[SCAN_ALL] Released at {sq}")

        # Return home before next
        robot.arm.move_pose(home_pose)


def pick_and_place_all():
    """
    For each square A1…D5:
      1) Go HOME → square pick → suction on
      2) Return HOME → camera position → suction off
      3) Return HOME
    """
    for sq, pick_pose in pick_positions.items():
        # Pick from square
        robot.arm.move_pose(home_pose)
        robot.arm.move_pose(pick_pose)
        robot.tool.grasp_with_tool()
        print(f"[PICK_ALL] Picked up {sq}")

        # Go back home then to camera and release
        robot.arm.move_pose(home_pose)
        robot.arm.move_pose(card_position)
        robot.tool.release_with_tool()
        print(f"[PICK_ALL] Released at camera for {sq}")

        # Return home before next
        robot.arm.move_pose(home_pose)

if __name__ == "__main__":
    # First, run the scan‐all routine
    print("=== Running full scan cycle ===")
    scan_all_cards()

    # Then, run the pick‐and‐place cycle
    print("=== Running full pick‐and‐place cycle ===")
    pick_and_place_all()
