import cv2
import os
import time
import numpy as np
from memory_queues import square_queue, gui_queue
from memory_logic import register_card, reset_game
from sift_utils import *
from recorded_positions import pick_positions, drop_positions, home_pose, scan_pose, CARD_BOX
from pyniryo2 import NiryoRobot, NiryoRos, Vision

import pyniryo

# -------------------- Robot Setup --------------------
robot_ip_address = "169.254.200.200"
robot = NiryoRobot(robot_ip_address)
robot.arm.calibrate_auto()
robot.tool.release_with_tool()    # ensure vacuum off
robot.arm.move_pose(home_pose)

image_save_dir = "scanned_cards"
os.makedirs(image_save_dir, exist_ok=True)

stable_wait_time = 2.0  # seconds card must stay stable

def is_at_scan_pose(current, target, tol=0.1):
    # only compare X,Y,Z
    return all(abs(c - t) < tol for c, t in zip(current[:3], target[:3]))

# -------------------- Card Scanning --------------------
def scan_card_image(square_id):
    # 1) Verify pose
    current_pose = [round(v, 2) for v in robot.arm.get_pose().to_list()]
    target_pose = [round(v, 2) for v in scan_pose]
    print(f"[DEBUG] Current pose")
    print(f"[DEBUG] Target scan pose")

    if not is_at_scan_pose(current_pose, target_pose, tol=0.1):
        print("[SKIP] Not at scan pose.")
        return None

    # 2) Init camera
    ros_instance = NiryoRos("169.254.200.200")
    vision = Vision(ros_instance)

    print(f"[SCAN] Looking for card at {square_id}")
    last_center = stable_since = detection_time = None
    last_box_debug = 0
    start_time = time.time()
    while True:
        try:
            # Step 1: Get image from Niryo camera
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

            # Step 2: Resize and mask
            try:
                frame_resized = cv2.resize(img, (640, 480))
            except Exception as e:
                print("[ERROR] cv2.resize failed:", e)
                return None

            masked = mask_outside_card(frame_resized, CARD_BOX)

            disp, box = draw_oriented_bounding_box(masked.copy())

            cv2.imwrite("debug_preview.jpg", frame_resized)
            cv2.imwrite("debug_masked.jpg", masked)

            # Step 4: Stability tracking
            t = time.time()
            if box is not None and box.shape == (4, 2):
                center = tuple(np.mean(box, axis=0).astype(int))
                if last_center and np.linalg.norm(np.array(center) - np.array(last_center)) < 10:
                    if stable_since is None:
                        stable_since = t
                    elif not detection_time and (t - stable_since) >= stable_wait_time:
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

                    # Step 5: Feature extraction
                    retry_count = 0
                    while retry_count < 5:
                        mean_vec, descriptors = extract_sift_signature(card)
                        if mean_vec is not None and descriptors is not None:
                            break

                        print(f"[WARN] No features found for {square_id}. Retrying scan... (attempt {retry_count+1})")

                        time.sleep(0.7)

                        retry_count += 1
                    if mean_vec is None:
                        print("[FATAL ERROR] Failed to extract features after retries.")
                        return None

                    # Step 6: Save & register
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
                    print("[ERROR] Timed out: Could not detect a valid bounding box in 10 seconds.")
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

            # --- THIS IS THE FIX ---
            # Check if the item from the queue is the difficulty setting dictionary
            if isinstance(queue_item, dict):
                if queue_item.get("event") == "set_difficulty":
                    # Forward the dictionary to memory_logic to handle it
                    register_card(queue_item, None, None, None)
                    continue # Skip the rest of the loop and wait for a real square_id
                else:
                    # Handle other potential dictionary messages if you add them later
                    print(f"[ROBOT] Received unknown dictionary message: {queue_item}")
                    continue
            
            # If it's not a dictionary, it must be a square_id string
            square_id = queue_item
            # --- END OF FIX ---

            if square_id == "reset_game":
                print("[ROBOT] Received reset command.")
                reset_game()
                continue

            print(f"[ROBOT] Received square: {square_id}")
            pick_pose = pick_positions.get(square_id)
            drop_pose = drop_positions.get(square_id)

            if pick_pose is None or drop_pose is None:
                print(f"[ERROR] Missing pose for {square_id}")
                continue

            # ---- PICK ----
            print(f"[MOVE] Preparing to pick {square_id}")
            if square_id.startswith('D'):
                print(f"[MOVE] Approaching row D. Moving to drop pose for {square_id} first.")
                robot.arm.move_pose(drop_pose)
            print(f"[MOVE] Moving to pick pose for {square_id}")
            robot.arm.move_pose(pick_pose)
            robot.tool.grasp_with_tool()
            robot.arm.move_pose(drop_pose)

            # ---- MOVE → SCAN ----
            print(f"[MOVE] Going to scan pose")
            robot.arm.move_pose(scan_pose)

            # ---- SCAN ----
            result = scan_card_image(square_id)
            if result is None:
                print(f"[WARN] Skipped scanning {square_id}.")

            # ---- DROP ----
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