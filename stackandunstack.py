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
        stack_safe_pose[2] += 0.0005 # Add safe clearance

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

    # 2. Execute the 20 pick-and-place movements
    safe_move(robot, home_pose)
    
    card_placed_count = 0

    for stack_id in ["L1", "L2", "R1", "R2"]:
        for i in range(5):
            target_id = target_slots.pop(0)

            # --- Get Poses ---
            stack_pick_pose = STACKS_DATA.get(stack_id)[:]

            # Adjust Z value based on pick count
            if i < 2:
                stack_pick_pose[2] = 0.055
            else:
                stack_pick_pose[2] = 0.05

            # --- Define a safe height above the stack ---
            stack_safe_pose = stack_pick_pose[:]
            stack_safe_pose[2] += 0.03  

            target_place_pose = drop_positions.get(target_id)
            
            if not stack_pick_pose or not target_place_pose:
                print(f"[ERROR] Missing pose for stack {stack_id} or target {target_id}. Aborting.")
                return

            print(f"[MOVE] Placing card {card_placed_count+1}/20: From {stack_id} to {target_id}")

            try:
                # A. Pick from Stack (Go to position, Pick)
                safe_move(robot, stack_pick_pose)
                robot.tool.grasp_with_tool()

                # B. Lift the card to a safe height (NEW)
                safe_move(robot, stack_safe_pose)

                # C. Move to Target and Drop
                safe_move(robot, target_place_pose)
                robot.tool.release_with_tool()

                # D. Return to the safe height above the stack (NEW)
                safe_move(robot, stack_safe_pose)
                
                # E. Return to the stack pick pose for the next iteration
                safe_move(robot, stack_pick_pose)
                
                card_placed_count+=1

            except Exception as e:
                print(f"[FATAL ERROR] Robot movement failed during placement: {e}")
                robot.tool.release_with_tool()
                safe_move(robot, home_pose)
                return

    print("[SETUP] Card placement complete.")
    safe_move(robot, home_pose)



# --- Inside your robot control file (e.g., memory_robot.py or stackandunstack.py) ---

# NOTE: Ensure L1_POSE, L2_POSE, R1_POSE, R2_POSE, robot, pick_positions, 
# home_pose, and CARD_THICKNESS are accessible.

# Global state to track ALL cards disposed so far
TOTAL_DISPOSED_CARDS = 0 
CARD_THICKNESS = 0.003
CARDS_PER_STACK = 5

# Array of all four stack poses in sequence
STACK_POSES_SEQUENCE = [L1, L2, R1, R2] 


def dispose_card_2_held(robot, card_id):
    """
    Disposes of the currently held card (Card 2) by moving directly to the stack,
    dropping it, and lifting up for the next move, skipping all intermediate poses.
    """
    global TOTAL_DISPOSED_CARDS
    
    # 1. DETERMINE TARGET STACK (Ignoring thickness, Z is fixed)
    stack_index = TOTAL_DISPOSED_CARDS // CARDS_PER_STACK 
    base_stack_pose = STACK_POSES_SEQUENCE[stack_index]
    stack_target_pose = base_stack_pose[:] # Use fixed Z
    
    # We must calculate a clearance height above the stack to avoid collision on exit
    stack_clearance_pose = stack_target_pose[:]
    stack_clearance_pose[2] += 0.05 # Add a minimal clearance (e.g., 5cm)

    print(f"[DISPOSE] Stacking {card_id} (HELD) on Stack {stack_index+1} (Fixed Z)")

    try:
        # A. Move to Stack
        # Move directly to the clearance pose above the stack
        robot.arm.move_pose(stack_clearance_pose) 
        robot.arm.move_pose(stack_target_pose) # Drop down to fixed Z
        robot.tool.release_with_tool()
        
        # B. Lift and Update Counter
        robot.arm.move_pose(stack_clearance_pose) # Lift up to clear the card
        TOTAL_DISPOSED_CARDS += 1
        return True

    except Exception as e:
        print(f"[FATAL ERROR] Disposal failed for HELD card {card_id}: {e}")
        robot.tool.release_with_tool()
        return False

# --- Inside your robot control file (e.g., memory_robot.py) ---

def dispose_card_1_on_board(robot, card_id):
    """
    Disposes of the card currently ON THE BOARD (Card 1), picking it up
    and placing it on the stack without using intermediate home poses.
    """
    global TOTAL_DISPOSED_CARDS
    
    # 1. DETERMINE TARGET STACK
    stack_index = TOTAL_DISPOSED_CARDS // CARDS_PER_STACK 
    base_stack_pose = STACK_POSES_SEQUENCE[stack_index]
    
    # Calculate fixed Z poses
    stack_target_pose = base_stack_pose[:] 
    stack_clearance_pose = stack_target_pose[:]
    stack_clearance_pose[2] += 0.05 
    
    board_pick_pose = pick_positions.get(card_id)
    board_clearance_pose = drop_positions.get(card_id) # Use drop_pose for board clearance

    if not board_pick_pose or not board_clearance_pose:
        print(f"[ERROR] Missing pick pose for {card_id}. Cannot dispose.")
        return False

    print(f"[DISPOSE] Picking {card_id} from board and stacking on Stack {stack_index+1}")

    try:
        # A. Pick from Board (Go to clearance, pick, then lift)
        robot.arm.move_pose(board_clearance_pose)
        robot.arm.move_pose(board_pick_pose)
        robot.tool.grasp_with_tool()
        robot.arm.move_pose(board_clearance_pose) # Lift the card up for transit
        
        # B. Move to Stack (Travel from board clearance pose directly to stack clearance pose)
        robot.arm.move_pose(stack_clearance_pose) 
        robot.arm.move_pose(stack_target_pose) # Drop down
        robot.tool.release_with_tool()
        
        # C. Lift and Update Counter
        robot.arm.move_pose(stack_clearance_pose) 
        TOTAL_DISPOSED_CARDS += 1
        
        return True
    
    except Exception as e:
        print(f"[FATAL ERROR] Disposal failed for ON-BOARD card {card_id}: {e}")
        robot.tool.release_with_tool()
        return False

if __name__ == "__main__":
    from pyniryo2 import NiryoRobot
    robot = NiryoRobot(ROBOT_IP_ADDRESS)
    robot.tool.release_with_tool()
    robot.arm.calibrate_auto()
    place_initial_cards(robot)