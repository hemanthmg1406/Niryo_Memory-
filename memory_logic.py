import numpy as np
import time
import random
import threading
from sklearn.decomposition import PCA
from memory_queues import gui_queue, square_queue
from sift_utils import compute_knn_match_score
from user_feedback import play_sound  

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

# ---------------------- CONFIG ----------------------
PCA_DIMS                  = 3
MATCH_DISTANCE_THRESHOLD  = 0.4
MATCH_KNN_SCORE_THRESHOLD = 0.3

# ---------------------- MAIN API ----------------------
def register_card(square_id, mean_vec, raw_desc, image_path, debug=False):
    global memory_board, turn_state, matched_squares, current_turn, last_flipped
    global score_human, score_robot

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
        return {"wait_second": True}

    # 6) Second card → compare
    sq1   = turn_state["first_square"]
    mean1 = turn_state["first_mean"]
    desc1 = turn_state["first_desc"]
    reset_turn_state()
    print(f"[LOGIC] Comparing {sq1} vs {square_id}…")
    match, d, knn = check_match(mean1, mean_vec, desc1, raw_desc)
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
        # Play correct-match sound/LED
        play_sound("correct_match_human")

        # Mark matched
        matched_squares.update([sq1, square_id])
        memory_board[sq1]["matched"]       = True
        memory_board[square_id]["matched"] = True

        # --- INCREMENT SCORE ---
        if current_turn == "human":
            score_human += 1
        else:
            score_robot += 1

        # Notify GUI of match
        gui_queue.put({
            "status":  "matched",
            "squares": [sq1, square_id]
        })
        # Send updated scores
        gui_queue.put({
            "event":       "score",
            "human_score": score_human,
            "robot_score": score_robot,
        })
        print(f"[LOGIC] Pair matched: {sq1}, {square_id} → +1 {current_turn}")
        log_move("match", (sq1, square_id))
        # Continue same turn
        advance_to_next_turn()

    else:
        # Play wrong-match sound/LED (human or robot)
        if current_turn == "human":
            play_sound("wrong_match_human")
        else:
            play_sound("wrong_match_robot")

        # Flip back
        gui_queue.put({
            "status":  "flip_back",
            "squares": [sq1, square_id]
        })
        print(f"[LOGIC] No match → FLIP_BACK {sq1},{square_id}")
        log_move("mismatch", (sq1, square_id))

        # Switch turn
        new_turn = switch_turn()
        # Play turn-start sound/LED
        if new_turn == "human":
            play_sound("human_turn")
        else:
            play_sound("robot_turn")

        gui_queue.put({
            "event":  "turn",
            "player": new_turn
        })
        print(f"[LOGIC] Turn → {new_turn}")

        # **Schedule the robot’s move automatically**
        if new_turn == "robot":
            picks = robot_play()
            for pick in picks:
                square_queue.put(pick)

    return result

# ---------------------- ROBOT STRATEGY ----------------------
def robot_play(debug=False):
    print("[ROBOT PLAY] Planning robot move...")
    # Play robot-turn sound/LED at start
    play_sound("robot_turn")

    all_squares = [r + c for r in "ABCD" for c in "12345"]
    seen        = set(memory_board.keys())
    matched     = matched_squares
    unmatched   = [sq for sq in seen if sq not in matched]

    valid_unmatched = [
        sq for sq in unmatched
        if memory_board[sq].get("mean") is not None and memory_board[sq].get("desc") is not None
    ]

    # --- STRATEGY 1: Confident match ---
    for i in range(len(valid_unmatched)):
        for j in range(i + 1, len(valid_unmatched)):
            sq1, sq2 = valid_unmatched[i], valid_unmatched[j]
            card1, card2 = memory_board[sq1], memory_board[sq2]
            if is_match(card1["mean"], card1["desc"], card2["mean"], card2["desc"]):
                log_move("robot_matched_pair", (sq1, sq2))
                square_queue.put(sq1)
                square_queue.put(sq2)
                return

    # --- STRATEGY 2: Flip unseen ---
    unseen = [sq for sq in all_squares if sq not in seen]
    if len(unseen) >= 2:
        a, b = random.sample(unseen, 2)
        log_move("robot_flip_unseen", (a, b))
        square_queue.put(a)
        square_queue.put(b)
        return
    elif len(unseen) == 1:
        a = unseen[0]
        fallback = [sq for sq in all_squares if sq != a and sq not in matched]
        b = random.choice(fallback) if fallback else a
        log_move("robot_flip_unseen_and_fallback", (a, b))
        square_queue.put(a)
        square_queue.put(b)
        return

    # --- STRATEGY 3: Fallback unmatched ---
    remaining = [sq for sq in all_squares if sq not in matched]
    if len(remaining) >= 2:
        a, b = random.sample(remaining, 2)
        log_move("robot_fallback", (a, b))
        square_queue.put(a)
        square_queue.put(b)
        return

    # --- STRATEGY 4: Final single ---
    if len(remaining) == 1:
        log_move("robot_final_single", remaining[0])
        square_queue.put(remaining[0])
        square_queue.put(remaining[0])
        return

    # --- STRATEGY 5: Idle ---
    log_move("robot_idle", None)

# ---------------------- HELPERS ----------------------
def check_match(m1, m2, d1, d2):
    vecs = np.array([m1, m2])
    pca  = PCA(n_components=min(PCA_DIMS, vecs.shape[0]))
    v3   = pca.fit_transform(vecs)
    dist = np.linalg.norm(v3[0] - v3[1])
    knn  = compute_knn_match_score(d1, d2)
    return (knn >= MATCH_KNN_SCORE_THRESHOLD or dist <= MATCH_DISTANCE_THRESHOLD), dist, knn

def is_match(m1, d1, m2, d2):
    try:
        return check_match(m1, m2, d1, d2)[0]
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

def advance_to_next_turn():
    """
    Called after a match or mismatch. Decides who plays next and re-triggers robot if needed.
    """
    gui_queue.put({"status": "turn", "player": current_turn})
    if current_turn == "robot":
        picks = robot_play()
        for sq in picks:
            square_queue.put(sq)

def reset_game():
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
    gui_queue.put({"status":"reset"})
    gui_queue.put({"event":"turn","player":"human"})
    # Play human-turn sound on fresh start
    play_sound("human_turn")

def get_turn():     return current_turn
def is_game_over(): return len(matched_squares) >= len(memory_board)
