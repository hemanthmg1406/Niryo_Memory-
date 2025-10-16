import numpy as np
import time
import random
import threading
from sklearn.decomposition import PCA
import sys, queue
import os
import glob
from pyniryo2 import NiryoRobot
from memory_queues import gui_queue, square_queue
from sift_utils import compute_knn_match_score
from user_feedback import play_sound
from robot_interface import set_robot_led
from config import (
    MATCH_DISTANCE_THRESHOLD,
    MATCH_KNN_SCORE_THRESHOLD,
    PCA_DIMS,
    DIFFICULTY_DEFAULT, ROBOT_IP_ADDRESS
)
from stackandunstack import dispose_card_1_on_board,dispose_card_2_held


# ---------------------- GLOBALS ----------------------
DIFFICULTY = DIFFICULTY_DEFAULT
audio_profile = "adult"  # Default audio profile

robot=NiryoRobot(ROBOT_IP_ADDRESS)


# ---------------------- GAME STATE ----------------------
memory_board    = {}          # square_id: {mean, desc, matched}
matched_squares = set()
game_history    = []          # Log of all moves and decisions

turn_state = {
    "first_square": None,
    "first_mean":   None,
    "first_desc":   None
}

last_flipped    = []
current_turn    = "human"

# ---------------------- SCORE ----------------------
score_human = 0
score_robot = 0


# ---------------------- MAIN API ----------------------
 # Ensure queue is imported at the top of memory_logic.py

def register_card(square_id, mean_vec, raw_desc, image_path, debug=False):
    global memory_board, turn_state, matched_squares, current_turn, last_flipped
    global score_human, score_robot, DIFFICULTY, audio_profile

    # --- START DICTIONARY MESSAGE ROUTING ---
    if isinstance(square_id, dict):
        event = square_id.get("event")

        # Existing logic for setting difficulty
        if event == "set_difficulty":
            DIFFICULTY = square_id.get("difficulty", "hard")
            audio_profile = square_id.get("audio_profile", "adult")
            print(f"[LOGIC] Difficulty set to: {DIFFICULTY}")
            print(f"[LOGIC] Audio profile set to: {audio_profile}")
            return {"difficulty_set": True}

        # NEW LOGIC FOR GET_HINT
        elif event == "GET_HINT":
            sq1, sq2 = find_hint_pair()
            if sq1 and sq2:
                gui_queue.put({"event": "HINT_FLASH", "squares": [sq1, sq2]})
            else:
                gui_queue.put({
                    "event": "SCREEN_MESSAGE",
                    "text": "Niryo: I don't know any pairs yet!",
                    "duration": 3000
                })
                print("[LOGIC] No known pairs available for hint.")
            return {"hint_requested": True}


        elif event in ["RESTART_GAME", "GOTO_INTRO", "reset_game", "collect_cards", "place_cards"]:
            # Since the robot thread handles the physical action, the logic thread simply
            # acknowledges the command and exits without checking for a card.
            return {"command_received": True}

        # FINAL FALLBACK: If a dictionary is completely unrecognized, exit safely.
        return {"unrecognized_command": True}


    # 1) Skip if already matched
    if square_id in matched_squares:
        if debug: print(f"[SKIP] {square_id} already matched.")
        return {"skip": True}

    # 2) Save features & log
    memory_board[square_id] = {"mean": mean_vec, "desc": raw_desc, "matched": False}

    # 3) Tell GUI to reveal
    gui_queue.put({
        "status":     "reveal",
        "square":     square_id,
        "image_path": image_path
    })
    print(f"[LOGIC] Sent REVEAL → GUI for {square_id}")

    # 4) Track flips & log
    last_flipped.append(square_id)
    if len(last_flipped) > 2:
        last_flipped[:] = last_flipped[-2:]
    log_move("flip", square_id)

    # 5) First card? wait for second
    if turn_state["first_square"] is None:
        turn_state["first_square"] = square_id
        turn_state["first_mean"]   = mean_vec
        turn_state["first_desc"]   = raw_desc

        # --- NEW LOGIC: CHECK FOR IMMEDIATE ROBOT MATCH (INTERRUPT) ---
        if current_turn == "robot":
            match_found = False
            # Iterate through all cards currently in the robot's memory
            for sq_id, card_data in memory_board.items():
                # Skip the card we just flipped, or any card already matched
                if sq_id == square_id or sq_id in matched_squares:
                    continue

                # Check for a match between the current flip (square_id) and the memory card (sq_id)
                if is_match(square_id, mean_vec, raw_desc, sq_id, card_data["mean"], card_data["desc"]):
                    print(f"[ROBOT INTERCEPT] Found immediate match for {square_id}: {sq_id}")
                    log_move("robot_intercept_pick", (square_id, sq_id))

                    # Interruption: Enqueue the correct SECOND pick (sq_id)
                    square_queue.put(sq_id)
                    match_found = True
                    break # Stop search after finding the first match

            # If a match was found, the robot has a pre-planned second pick (the incorrect one)
            # sitting in the queue. We must discard it.
            if match_found:
                try:
                    # Remove the incorrect pre-planned second pick from the queue.
                    bad_pick = square_queue.get_nowait()
                    print(f"[ROBOT INTERCEPT] Discarded incorrect planned pick: {bad_pick}")
                except queue.Empty:
                    # This is fine; it just means the robot's thread was slow and hadn't
                    # put the second pick in yet, or its strategy only returned one pick.
                    pass
        # --- END NEW LOGIC ---

        return {"wait_second": True}

    # 6) Second card → compare
    sq1   = turn_state["first_square"]
    mean1 = turn_state["first_mean"]
    desc1 = turn_state["first_desc"]
    reset_turn_state()
    print(f"[LOGIC] Comparing {sq1} vs {square_id}…")

    match, d, knn = check_match(sq1, mean1, desc1, square_id, mean_vec, raw_desc)

    reason = "KNN" if knn >= MATCH_KNN_SCORE_THRESHOLD else "PCA" if d <= MATCH_DISTANCE_THRESHOLD else "None"
    print(f"[LOGIC] Compared: PCA={d:.2f}, KNN={knn:.2f} → match={match}")

    # 7) Build result dict
    result = {
        "match":         match,
        "pca_distance":  d,
        "knn_score":     knn,
        "continue_turn": match,
        "debug_info":    f"PCA={d:.2f}, KNN={knn:.2f}"
    }

    if match:
        if current_turn == "human":
            play_sound(f"{audio_profile}/correct_match_human")
            score_human += 1
            set_robot_led(robot,"MATCH_HUMAN")
        else:
            play_sound(f"{audio_profile}/correct_match_robot")
            score_robot += 1
            set_robot_led(robot,"MATCH_ROBOT")
        time.sleep(1.0) # Pause to let user see the match LED
        gui_queue.put({"status":  "matched", "squares": [sq1, square_id]})
        gui_queue.put({"event": "score", "human_score": score_human, "robot_score": score_robot})
        dispose_card_2_held(robot,square_id)
        dispose_card_1_on_board(robot,sq1)

        matched_squares.update([sq1, square_id])
        memory_board[sq1]["matched"]       = True
        memory_board[square_id]["matched"] = True
        print(f"[LOGIC] Pair matched: {sq1}, {square_id} → +1 {current_turn}")
        log_move("match", (sq1, square_id))
        if is_game_over():
            winner = "Human" if score_human > score_robot else "Robot" if score_robot > score_human else "Tie"
            #sounds
            if winner == "Human":
                play_sound(f"{audio_profile}/human_win")
            else:
                play_sound(f"{audio_profile}/robot_win")

            #end of sounds
            gui_queue.put({
                "event": "game_over",
                "winner": winner,
                "human_score": score_human,
                "robot_score": score_robot
            })
            print(f"[LOGIC] GAME OVER: {winner} wins!")
            gui_queue.put({"event": "GOTO_INTRO"})
            
        else:
            # Continue same turn (only if game is NOT over)
            advance_to_next_turn()
        #robot.arm.move_pose(home_pose)
        return result
    else:
        if current_turn == "human":
            play_sound(f"{audio_profile}/wrong_match_human")
            set_robot_led(robot,"MISMATCH_HUMAN")
        else:
            play_sound(f"{audio_profile}/wrong_match_robot")
            set_robot_led(robot,"MISMATCH_ROBOT")
        time.sleep(1.0) # Pause to let user see the mismatch LED
        gui_queue.put({"status":  "flip_back", "squares": [sq1, square_id]})
        print(f"[LOGIC] No match → FLIP_BACK {sq1},{square_id}")
        log_move("mismatch", (sq1, square_id))
       # square_queue.put({"event": "DROP_CURRENT_CARD", "square": square_id})
        new_turn = switch_turn()
        if new_turn == "human":
            play_sound(f"{audio_profile}/human_turn")
        else:
            play_sound(f"{audio_profile}/robot_turn")
        gui_queue.put({"event":  "turn", "player": new_turn})
        print(f"[LOGIC] Turn → {new_turn}")

        if new_turn == "robot":
            square_queue.put({"event": "PLAN_NEXT_ROBOT_MOVE"})

    return result

# ---------------------- ROBOT STRATEGY ----------------------
def robot_play(debug=False):
    global DIFFICULTY
    print(f"[ROBOT PLAY] Planning robot move on {DIFFICULTY} difficulty...")
    # ... (Sound and initial setup code remains unchanged) ...

    all_squares = [r + c for r in "ABCD" for c in "12345"]
    seen = set(memory_board.keys())
    matched = matched_squares

    valid_unmatched = [
        sq for sq in seen
        if sq not in matched
        and memory_board[sq].get("mean") is not None
        and memory_board[sq].get("desc") is not None
    ]
    
    # ----------------------------------------------------------------------
    # --- STRATEGY 0: Confident Match (Memory Search - Hard/Medium only) ---
    # ----------------------------------------------------------------------
    if DIFFICULTY in ["hard", "medium"]: 
        if DIFFICULTY == "medium" and random.random() < 0.5: 
             pass
        else:
            for i in range(len(valid_unmatched)):
                for j in range(i + 1, len(valid_unmatched)):
                    sq1, sq2 = valid_unmatched[i], valid_unmatched[j]
                    card1, card2 = memory_board[sq1], memory_board[sq2]

                    if is_match(sq1, card1["mean"], card1["desc"], sq2, card2["mean"], card2["desc"]):
                        log_move("robot_confident_pair_match", (sq1, sq2))
                        return [sq1, sq2]
    
    # ----------------------------------------------------------------------
    # --- STRATEGY 1: Pure Random/Fallback (Primary strategy for Easy) ---
    # This strategy finds any two available cards and picks them.
    # ----------------------------------------------------------------------
    
    # This list contains ALL remaining unmatched cards, regardless of whether they have been "seen".
    remaining = [sq for sq in all_squares if sq not in matched] 
    
    if len(remaining) >= 2:
        a, b = random.sample(remaining, 2)
        
        # If Easy mode, execute this strategy and return immediately.
        if DIFFICULTY == "easy":
            log_move("robot_fallback_easy", (a, b))
            return [a, b]
            
    # ----------------------------------------------------------------------
    # --- STRATEGY 2: Flip unseen cards (Standard/Medium continuation) ---
    # This block executes ONLY if Hard/Medium failed their memory search and 
    # needs to decide where to reveal a new card.
    # ----------------------------------------------------------------------
    
    if DIFFICULTY in ["hard", "medium"]:
        unseen = [sq for sq in all_squares if sq not in seen]
        if len(unseen) >= 2:
            a, b = random.sample(unseen, 2)
            log_move("robot_flip_unseen", (a, b))
            return [a, b]
        elif len(unseen) == 1:
            a = unseen[0]
            fallback = [sq for sq in all_squares if sq != a and sq not in matched]
            b = random.choice(fallback) if fallback else a
            log_move("robot_flip_unseen_and_fallback", (a, b))
            return [a, b]
    
    # --- STRATEGY 3: Final single (For any mode) ---
    if len(remaining) == 1:
        log_move("robot_final_single", remaining[0])
        return [remaining[0], remaining[0]]

    # --- STRATEGY 4: Idle ---
    log_move("robot_idle", None)
    return []

# ---------------------- HELPERS ----------------------
def check_match(sq1_id, m1, d1, sq2_id, m2, d2):
    vecs = np.array([m1, m2])
    pca  = PCA(n_components=min(PCA_DIMS, vecs.shape[0]))
    v3   = pca.fit_transform(vecs)
    dist = np.linalg.norm(v3[0] - v3[1])
    knn  = compute_knn_match_score(d1, d2)
    print("-" * 50)
    print(f"[COMPARE] Checking pair: {sq1_id} vs {sq2_id}")
    print(f"[SCORE] PCA Distance: {dist:.4f} (Threshold <= {MATCH_DISTANCE_THRESHOLD})")
    print(f"[SCORE] KNN Score:    {knn:.4f} (Threshold >= {MATCH_KNN_SCORE_THRESHOLD})")

    match_pca = (dist <= MATCH_DISTANCE_THRESHOLD)
    match_knn = (knn >= MATCH_KNN_SCORE_THRESHOLD)

    match = match_pca or match_knn

    print(f"[RESULT] Match by PCA: {match_pca}, Match by KNN: {match_knn}")
    print(f"[RESULT] Final Match Decision: {match}")

    return match, dist, knn

def is_match(sq1_id, m1, d1,sq2_id, m2, d2):
    try:
        return check_match(sq1_id,m1, d1,sq2_id, m2, d2)[0]
    except KeyError as e:
        print(f"[LOGIC] is_match() KeyError: {e}")
        return False

def switch_turn():
    global current_turn
    current_turn = "robot" if current_turn == "human" else "human"
    return current_turn

def reset_turn_state():
    turn_state["first_square"] = None
    turn_state["first_mean"]   = None
    turn_state["first_desc"]   = None

def log_move(event, data):
    game_history.append({
        "event":     event,
        "data":      data,
        "turn":      current_turn,
        "timestamp": time.time()
    })

def find_hint_pair():
    """Searches memory for the first known, unmatched pair."""
    
    # We use the same powerful memory logic as the robot's Strategy 0
    valid_unmatched = [
        sq for sq in memory_board.keys() 
        if sq not in matched_squares
        and memory_board[sq].get("mean") is not None
        and memory_board[sq].get("desc") is not None
    ]
    
    # Check every known, unmatched pair
    for i in range(len(valid_unmatched)):
        for j in range(i + 1, len(valid_unmatched)):
            sq1, sq2 = valid_unmatched[i], valid_unmatched[j]
            card1, card2 = memory_board[sq1], memory_board[sq2]
            
            # Check for confident match
            if is_match(sq1, card1["mean"], card1["desc"], sq2, card2["mean"], card2["desc"]):
                # Found the pair!
                return sq1, sq2 

    return None, None # No known pair found

def advance_to_next_turn():
    gui_queue.put({"status": "turn", "player": current_turn})
    if current_turn == "robot":
        picks = robot_play()
        for sq in picks:
            square_queue.put(sq)

def reset_game(play_turn_sound=True): # <-- CHANGE #1: Add the argument
    global memory_board, matched_squares, current_turn, last_flipped, game_history
    global score_human, score_robot
    memory_board.clear()
    matched_squares.clear()
    last_flipped.clear()
    game_history.clear()
    reset_turn_state()
    current_turn = "human"
    score_human = 0
    score_robot = 0
    image_save_dir = "scanned_cards"
    for f in glob.glob(os.path.join(image_save_dir, "*")):
        try:
            os.remove(f)
        except OSError as e:
            print(f"[ERROR] Could not delete file {f}: {e}")
    gui_queue.put({"status":"reset"})
    gui_queue.put({"event":"turn","player":"human"})
    if play_turn_sound: # <-- CHANGE #2: Add this 'if' condition
        play_sound("human_turn")

def get_turn():
    return current_turn

def is_game_over():
    return len(matched_squares) == 20