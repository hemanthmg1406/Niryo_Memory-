import os
import time
import random
from pyniryo2 import NiryoRobot
from recorded_positions import pick_positions, drop_positions, home_pose, L1, L2, R1, R2
from config import ROBOT_IP_ADDRESS

CARD_THICKNESS = 0.003
CARDS_PER_STACK = 5
BOARD_ROWS = ["A", "B", "C", "D"]
ALL_SQUARE_IDS = [r + c for r in BOARD_ROWS for c in "12345"]

STACK_MAP = {
    "A": {"id": "L1", "pose": L1, "count": 0},
    "B": {"id": "L2", "pose": L2, "count": 0},
    "C": {"id": "R1", "pose": R1, "count": 0},
    "D": {"id": "R2", "pose": R2, "count": 0},
}
STACKS_DATA = {
    "L1": L1,
    "L2": L2,
    "R1": R1,
    "R2": R2,
}

def safe_move(robot, pose):
    """Helper function to execute arm movement with exception handling."""
    robot.arm.move_pose(pose)

def collect_cards_to_stacks(robot):

    print("[SETUP] Starting card collection from board...")
    safe_move(robot, home_pose)

    # Reset stack counts for a fresh run
    for info in STACK_MAP.values():
        info["count"] = 0

    for slot_id in ALL_SQUARE_IDS:
        row_id = slot_id[0]
        stack_info = STACK_MAP[row_id]

        board_pick_pose = pick_positions.get(slot_id)
        board_safe_pose = drop_positions.get(slot_id)

        if not board_pick_pose:
            print(f"[ERROR] Missing pick pose for {slot_id}. Skipping.")
            continue

        # Calculate the destination Z based on current stack count
        base_stack_z = stack_info["pose"][2]
        new_stack_pose = stack_info["pose"][:]
        new_stack_pose[2] = base_stack_z + (stack_info["count"] * CARD_THICKNESS)

        stack_safe_pose = new_stack_pose[:]
        stack_safe_pose[2] += 0.05 # Add safe clearance

        print(f"[MOVE] Collecting {slot_id} → {stack_info['id']} (Card height: {new_stack_pose[2]:.4f})")

        try:
            # A. Pick from Board (Approach, Pick, Lift)
            safe_move(robot, board_safe_pose)
            safe_move(robot, board_pick_pose)
            robot.tool.grasp_with_tool()
            safe_move(robot, board_safe_pose)

            # B. Move to Stack (Via Home, Approach Stack, Drop)
            safe_move(robot, stack_safe_pose)
            robot.tool.release_with_tool()

            # C. Return to Safe Height
            safe_move(robot, stack_safe_pose)

            # D. Update Stack Count
            stack_info["count"] += 1

        except Exception as e:
            print(f"[FATAL ERROR] Robot movement failed during collection of {slot_id}: {e}")
            robot.tool.release_with_tool()
            safe_move(robot, home_pose)
            return

    print("[SETUP] Card collection complete. Board cleared.")
    safe_move(robot, home_pose)


def place_initial_cards(robot):
    """
    Distributes 20 cards from the 4 fixed supply stacks (5 cards each)
    randomly onto the 20 board positions.
    """
    print("[SETUP] Starting automatic card placement...")

    # 1. Prepare sequence lists
    target_slots = ALL_SQUARE_IDS[:]
    random.shuffle(target_slots)

    source_picks_sequence = []
    for stack_id in STACKS_DATA.keys():
        source_picks_sequence.extend([stack_id] * CARDS_PER_STACK)

    # 2. Execute the 20 pick-and-place movements
    safe_move(robot, home_pose)

    for i in range(len(source_picks_sequence)):
        source_id = source_picks_sequence[i]
        target_id = target_slots[i]

        # --- Get Poses ---
        stack_pick_pose = STACKS_DATA.get(source_id)

        # Calculate a safe height pose above the stack for movement (Z + 0.05m)
        stack_safe_pose = stack_pick_pose[:]
        stack_safe_pose[2] += 0.05

        target_place_pose = pick_positions.get(target_id)
        target_safe_pose = drop_positions.get(target_id)

        if not stack_pick_pose or not target_place_pose:
            print(f"[ERROR] Missing pose for stack {source_id} or target {target_id}. Aborting.")
            return

        print(f"[MOVE] Placing card {i+1}/20: From {source_id} to {target_id}")

        try:
            # A. Pick from Stack (Approach, Pick, Lift)
            safe_move(robot, stack_safe_pose)
            safe_move(robot, stack_pick_pose)
            robot.tool.grasp_with_tool()
            safe_move(robot, stack_safe_pose)

            # B. Move to Target (Via Home, Approach Target, Drop)
            safe_move(robot, target_safe_pose)
            robot.tool.release_with_tool()

            # C. Return to Safe Height
            safe_move(robot, target_safe_pose)

        except Exception as e:
            print(f"[FATAL ERROR] Robot movement failed during placement: {e}")
            robot.tool.release_with_tool()
            safe_move(robot, home_pose)
            return

    print("[SETUP] Card placement complete.")
    safe_move(robot, home_pose)

if __name__ == "__main__":
    from pyniryo2 import NiryoRobot
    robot = NiryoRobot(ROBOT_IP_ADDRESS)
    robot.tool.release_with_tool()
    robot.arm.calibrate_auto()
    collect_cards_to_stacks(robot)