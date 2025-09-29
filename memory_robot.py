import cv2
import os
import time
import numpy as np
from memory_queues import square_queue, gui_queue
from memory_logic import register_card, reset_game
from sift_utils import *
from recorded_positions import pick_positions, drop_positions, home_pose, scan_pose
from pyniryo2 import NiryoRobot, NiryoRos, Vision
from config import ROBOT_IP_ADDRESS, STABLE_WAIT_TIME, CARD_BOX
import pyniryo
from user_feedback import play_sound
# --- NEW: Import the utility functions ---
from stackandunstack import collect_cards_to_stacks, place_initial_cards

# -------------------- Robot Setup --------------------

robot = NiryoRobot(ROBOT_IP_ADDRESS)
robot.arm.calibrate_auto()
robot.tool.release_with_tool()
robot.arm.move_pose(home_pose)

image_save_dir = "scanned_cards"
os.makedirs(image_save_dir, exist_ok=True)



def is_at_scan_pose(current, target, tol=0.1):
    return all(abs(c - t) < tol for c, t in zip(current[:3], target[:3]))

# -------------------- Card Scanning --------------------
def scan_card_image(square_id, max_scan_retries=3):
    current_pose = [round(v, 2) for v in robot.arm.get_pose().to_list()]
    target_pose = [round(v, 2) for v in scan_pose]
    print(f"[DEBUG] Current pose")
    print(f"[DEBUG] Target scan pose")

    if not is_at_scan_pose(current_pose, target_pose, tol=0.1):
        print("[SKIP] Not at scan pose.")
        return None

    ros_instance = NiryoRos("169.254.200.200")
    vision = Vision(ros_instance)

    print(f"[SCAN] Looking for card at {square_id}")
    last_center = stable_since = detection_time = None
    last_box_debug = 0
    start_time = time.time()
    
    while True:
        try:
            img_compressed = vision.get_img_compressed()
            if img_compressed is None:
                print("[ERROR] Could not get compressed image.")
                return None

            img_uncompressed = pyniryo.uncompress_image(img_compressed)
            if img_uncompressed is None:
                print("[ERROR] Failed to uncompress image.")
                return None

            camera_info = vision.get_camera_intrinsics()
            img = pyniryo.undistort_image(
                img_uncompressed,
                camera_info.intrinsics,
                camera_info.distortion
            )
          
            try:
                frame_resized = cv2.resize(img, (640, 480))
            except Exception as e:
                print("[ERROR] cv2.resize failed:", e)
                return None

            masked = mask_outside_card(frame_resized, CARD_BOX)
            disp, box = draw_oriented_bounding_box(masked.copy())

            cv2.imwrite("debug_preview.jpg", frame_resized)
            cv2.imwrite("debug_masked.jpg", masked)

            t = time.time()
            if box is not None and box.shape == (4, 2):
                center = tuple(np.mean(box, axis=0).astype(int))
                if last_center and np.linalg.norm(np.array(center) - np.array(last_center)) < 10:
                    if stable_since is None:
                        stable_since = t
                    elif not detection_time and (t - stable_since) >= STABLE_WAIT_TIME:
                        detection_time = t
                else:
                    stable_since = None
                last_center = center

                if detection_time and (t - detection_time) >= 1:
                    snap = masked.copy()
                    pts = box.astype('float32')
                    w = int(max(np.linalg.norm(pts[0] - pts[1]), np.linalg.norm(pts[2] - pts[3])))
                    h = int(max(np.linalg.norm(pts[1] - pts[2]), np.linalg.norm(pts[3] - pts[0])))
                    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype='float32')

                    try:
                        M = cv2.getPerspectiveTransform(pts, dst)
                        card = cv2.warpPerspective(snap, M, (w, h))
                    except cv2.error as e:
                        print("[ERROR] Perspective transform failed:", e)
                        return None

                    card = auto_crop_inside_white_edges(card)
                    cv2.destroyAllWindows()

                    retry_count = 0
                    while retry_count < max_scan_retries:
                        mean_vec, descriptors = extract_sift_signature(card)
                        if mean_vec is not None and descriptors is not None:
                            break

                        print(f"[WARN] No features found for {square_id}. Retrying scan... (attempt {retry_count+1}/{max_scan_retries})")
                        time.sleep(0.7)
                        retry_count += 1
                    
                    if mean_vec is None:
                        print(f"[FAIL] Failed to extract features after {max_scan_retries} software retries.")
                        return None 

                    filename = f"{square_id}.jpg"
                    filepath = os.path.join(image_save_dir, filename)
                    cv2.imwrite(filepath, card)
                    print(f"[ROBOT] Captured {square_id} → {filepath}")

                    result = register_card(square_id, mean_vec, descriptors, filepath, debug=True)

                    gui_queue.put({
                        "status": "reveal",
                        "square": square_id,
                        "image_path": filepath
                    })
                    return result
            else:
                now = time.time()
                if now - last_box_debug > 3.0:
                    print("[DEBUG] No valid bounding box found.")
                    last_box_debug = now

                if now - start_time > 15.0:
                    print("[ERROR] Timed out: Could not detect a valid bounding box in 15 seconds.")
                    return None

        except Exception as e:
            print("[FATAL ERROR] Exception in scan_card_image:", e)
            return None

# -------------------- Main Loop --------------------
def main_loop():
    print("[READY] Awaiting square picks...")
    robot.arm.move_pose(home_pose)

    try:
        while True:
            if square_queue.empty():
                time.sleep(0.05)
                continue

            queue_item = square_queue.get()

            # --- UPDATED: Expanded to handle new utility commands ---
            if isinstance(queue_item, dict):
                event = queue_item.get("event")
                if event == "set_difficulty":
                    register_card(queue_item, None, None, None)
                elif event == "collect_cards":
                    print("[ROBOT] Received 'collect_cards' command. Executing...")
                    collect_cards_to_stacks(robot)
                    print("[ROBOT] Card collection finished.")
                elif event == "place_cards":
                    print("[ROBOT] Received 'place_cards' command. Executing...")
                    place_initial_cards(robot)
                    print("[ROBOT] Card placement finished.")
                else:
                    print(f"[ROBOT] Received unknown dictionary message: {queue_item}")
                continue
            
            square_id = queue_item
            
            # --- UPDATED: HANDLE DICTIONARY MESSAGES (Difficulty, Reset, etc.) ---
            if isinstance(queue_item, dict):
                event = queue_item.get("event")
                if event == "set_difficulty":
                    register_card(queue_item, None, None, None)
                elif event == "reset_game":
                    # Get the flag from the message, default to True if not found
                    play_sound_flag = queue_item.get("play_sound", True)
                    print(f"[ROBOT] Received reset command (Play Sound: {play_sound_flag}).")
                    reset_game(play_turn_sound=play_sound_flag)
                elif event == "collect_cards":
                    print("[ROBOT] Received 'collect_cards' command. Executing...")
                    collect_cards_to_stacks(robot)
                    print("[ROBOT] Card collection finished.")
                elif event == "place_cards":
                    print("[ROBOT] Received 'place_cards' command. Executing...")
                    place_initial_cards(robot)
                    print("[ROBOT] Card placement finished.")
                else:
                    print(f"[ROBOT] Received unknown dictionary message: {queue_item}")
                continue
            
            # This handles the old string-based reset command if it's still sent from somewhere
            if queue_item == "reset_game":
                print("[ROBOT] Received legacy reset command.")
                reset_game(play_turn_sound=True) 
                continue

            square_id = queue_item
            
            # --- HANDLE LEGACY RESET COMMAND (optional fallback) ---
            if queue_item == "reset_game":
                print("[ROBOT] Received legacy reset command.")
                reset_game(play_turn_sound=True) 
                continue

            square_id = queue_item

            print(f"[ROBOT] Received square: {square_id}")
            pick_pose = pick_positions.get(square_id)
            drop_pose = drop_positions.get(square_id)

            if pick_pose is None or drop_pose is None:
                print(f"[ERROR] Missing pose for {square_id}")
                continue

            result = None
            total_attempt_cycles = 2
            
            for attempt_cycle in range(total_attempt_cycles):
                if attempt_cycle == 0:
                    print(f"[MOVE] Preparing to pick {square_id} (Cycle {attempt_cycle+1})")
                    if square_id.startswith('D'):
                        print(f"[MOVE] Approaching row D. Moving to drop pose for {square_id} first.")
                        robot.arm.move_pose(drop_pose)
                    robot.arm.move_pose(pick_pose)
                    robot.tool.grasp_with_tool()
                    robot.arm.move_pose(drop_pose)

                elif attempt_cycle == 1:
                    print(f"[MOVE] Repicking {square_id} for second chance.")
                    robot.tool.release_with_tool()
                    time.sleep(1.0)
                    
                    robot.arm.move_pose(pick_pose)
                    robot.tool.grasp_with_tool()
                    robot.arm.move_pose(drop_pose)

                print(f"[MOVE] Going to scan pose")
                robot.arm.move_pose(scan_pose)

                result = scan_card_image(square_id) 

                if result is not None:
                    break

            if result is None:
                print(f"[WARN] Failed to scan {square_id} after all attempts. Signaling scan failure.")
                gui_queue.put({"status": "scan_fail", "square": square_id})
                robot.tool.release_with_tool()
                robot.arm.move_pose(home_pose)
                continue

            play_sound("placing")
            robot.arm.move_pose(home_pose)
            robot.arm.move_pose(drop_pose)
            robot.tool.release_with_tool()
            print(f"[DROP] Released at {square_id}")

            gui_queue.put({
                "status": "dropped",
                "square": square_id
            })

            robot.arm.move_pose(home_pose)

    except KeyboardInterrupt:
        print("[STOP] Interrupted by user.")
    finally:
        cv2.destroyAllWindows()
        robot.arm.move_pose(home_pose)


if __name__ == "__main__":
    main_loop()