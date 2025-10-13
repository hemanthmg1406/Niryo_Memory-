import cv2
import os
import time
import numpy as np
from memory_queues import square_queue, gui_queue
from memory_logic import register_card, reset_game,robot_play, get_card_category
from sift_utils import *
from recorded_positions import *
from pyniryo2 import NiryoRobot, NiryoRos, Vision
from config import ROBOT_IP_ADDRESS, STABLE_WAIT_TIME, CARD_BOX
import pyniryo
from user_feedback import play_sound
from stackandunstack import collect_cards_to_stacks, place_initial_cards

# -------------------- Robot Setup --------------------

robot = NiryoRobot(ROBOT_IP_ADDRESS)
robot.arm.calibrate_auto()
robot.tool.release_with_tool()
robot.arm.move_pose(home_pose)

image_save_dir = "scanned_cards"
os.makedirs(image_save_dir, exist_ok=True)
is_scanning = False


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
                    
                    category, sentence , audio_path= get_card_category(mean_vec)
                    
                    if category:
                        print(f"[IDENTIFY] CARD FOUND: {category}")
                        print(f"[IDENTIFY] ROBOT ANNOUNCES: {sentence}")
                        # NOTE: Ensure play_sound is accessible/imported in memory_robot.py
                        #play_sound(audio_path)
                    else:
                        print("[IDENTIFY] No matching category found.")
                    
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

                if now - start_time > 10.0:
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
            # Setting LED state based on turn (Assuming set_robot_led is fixed elsewhere)
            # if get_turn() == "robot": set_robot_led(robot, "PLANNING")
            # else: set_robot_led(robot, "WAITING")

            if square_queue.empty():
                time.sleep(0.05)
                continue

            queue_item = square_queue.get()
            
            # --- START: HANDLE DICTIONARY MESSAGES (INCLUDING HINT) ---
            if isinstance(queue_item, dict):
                event = queue_item.get("event")
                
                # --- CRITICAL FIX: FORWARD ALL NON-MOVEMENT COMMANDS TO LOGIC ---
                # This handles 'set_difficulty', 'GET_HINT', 'RESTART_GAME', 'GOTO_INTRO', etc.
                register_card(queue_item, None, None, None)
                
                # --- EXECUTE PHYSICAL COMMANDS LOCALLY (IF APPLICABLE) ---
                
                if event == "collect_cards":
                    print("[ROBOT] Received 'collect_cards' command. Executing...")
                    collect_cards_to_stacks(robot)
                    print("[ROBOT] Card collection finished.")
                elif event == "place_cards":
                    print("[ROBOT] Received 'place_cards' command. Executing...")
                    gui_queue.put({"event": "SCREEN_MESSAGE", "text": "Placing cards..."})
                    place_initial_cards(robot)
                    gui_queue.put({"event": "SCREEN_MESSAGE", "text": "Card placement finished."})
                    print("[ROBOT] Card placement finished.")
               
                
                elif event == "PLAN_NEXT_ROBOT_MOVE":
                    print("[ROBOT] Received PLAN_NEXT_ROBOT_MOVE command. Executing planning.")
                    picks = robot_play()
                    for pick in picks:
                        square_queue.put(pick)
                    print(f"[ROBOT] Enqueued next moves: {picks}")
                elif event in ["RESTART_GAME", "GOTO_INTRO"]:
                    # Note: Physical halt logic would be placed here if needed.
                    pass
                
                # We skip the rest of the main loop since the command was handled.
                continue
            
            # --- END: HANDLE DICTIONARY MESSAGES ---
            
            # --- HANDLE LEGACY/STRING MESSAGES ---
            
            # Remove redundant 'reset_game' checks, rely on dictionary message reset
            square_id = queue_item
            if square_id == "reset_game":
                 print("[ROBOT] Received legacy/redundant reset command. Ignoring.")
                 continue
            print(f"[ROBOT] Received square: {square_id}")
            pick_pose = pick_positions.get(square_id)
            drop_pose = drop_positions.get(square_id)

            if pick_pose is None or drop_pose is None:
                print(f"[ERROR] Missing pose for {square_id}")
                continue
            time.sleep(0.3) # Brief pause before action
            # --- START: PICK, SCAN, DROP SEQUENCE ---
            result = None
            total_attempt_cycles = 2
            
            for attempt_cycle in range(total_attempt_cycles):
                
                # 1. PICK MOVEMENT LOGIC (Optimized and simplified)
                print(f"[MOVE] Cycle {attempt_cycle+1}: Picking {square_id}")
                if attempt_cycle == 0:
                    # Initial pick
                    # NOTE: Assuming row D check for approaching via drop_pose happens here or is omitted for simplicity
                    pass
                elif attempt_cycle == 1:
                    # Repick logic: Release, wait, grasp
                    robot.tool.release_with_tool()
                    time.sleep(1.0)
                    robot.arm.move_pose(drop_pose) # Move to drop height first
                
                robot.arm.move_pose(pick_pose)
                robot.tool.grasp_with_tool()
                robot.arm.move_pose(drop_pose) # Lift to safe height

                # 2. SCAN MOVEMENT AND EXECUTION
                print(f"[MOVE] Going to scan pose")
                robot.arm.move_pose(scan_pose)
                is_scanning = True
                result = scan_card_image(square_id)
                is_scanning = False
                if result is not None:
                    break # Success!

            # --- END: PICK, SCAN, DROP SEQUENCE ---

            if result is None:
                # Total failure after all retries
                print(f"[WARN] Failed to scan {square_id} after all attempts. Signaling scan failure.")
                gui_queue.put({"status": "scan_fail", "square": square_id})
                
                # Cleanup: Release tool and go home
                robot.tool.release_with_tool()
                robot.arm.move_pose(home_pose)
                continue # Skip drop and go to next pick

            if result.get("match"):
                robot.arm.move_pose(home_pose)
                continue

            # ---- DROP (Only executes on successful scan) ----
            play_sound("placing") # Move this before the move
            robot.arm.move_pose(drop_pose) # Move to drop position
            robot.tool.release_with_tool()
            print(f"[DROP] Released at {square_id}")

            gui_queue.put({"status": "dropped", "square": square_id})
            robot.arm.move_pose(home_pose)

    except KeyboardInterrupt:
        print("[STOP] Interrupted by user.")
    finally:
        cv2.destroyAllWindows()
        robot.arm.move_pose(home_pose)

if __name__ == "__main__":
    main_loop()