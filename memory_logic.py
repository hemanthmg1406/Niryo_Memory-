import numpy as np
import time
import random
import threading
from sklearn.decomposition import PCA
from memory_queues import gui_queue, square_queue
from sift_utils import compute_knn_match_score

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

# ---------------------- CONFIG ----------------------
PCA_DIMS                  = 3
MATCH_DISTANCE_THRESHOLD  = 0.4
MATCH_KNN_SCORE_THRESHOLD = 0.3

# ---------------------- MAIN API ----------------------
def register_card(square_id, mean_vec, raw_desc, image_path, debug=False):
    global memory_board, turn_state, matched_squares, current_turn, last_flipped

    # 1) Skip if already matched
    if square_id in matched_squares:
        if debug: print(f"[SKIP] {square_id} already matched.")
        return {"skip": True}

    # 2) Save features & log
    memory_board[square_id] = {"mean": mean_vec, "desc": raw_desc, "matched": False}
    print(f"[LOGIC] memory_board[{square_id}] = {memory_board[square_id]}")

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
        # Mark matched
        matched_squares.update([sq1, square_id])
        memory_board[sq1]["matched"]       = True
        memory_board[square_id]["matched"] = True

        # Notify GUI of match
        gui_queue.put({
            "status":  "matched",
            "squares": [sq1, square_id]
        })
        # Update score
        gui_queue.put({
            "event":  "score",
            "player": current_turn
        })
        print(f"[LOGIC] Pair matched: {sq1}, {square_id} → +1 {current_turn}")
        log_move("match", (sq1, square_id))

    else:
        # Flip back
        gui_queue.put({
            "status":  "flip_back",
            "squares": [sq1, square_id]
        })
        print(f"[LOGIC] No match → FLIP_BACK {sq1},{square_id}")
        log_move("mismatch", (sq1, square_id))

        # Switch turn
        new_turn = switch_turn()
        gui_queue.put({
            "event":  "turn",
            "player": new_turn
        })
        print(f"[LOGIC] Turn → {new_turn}")

        # **Schedule the robot’s move automatically**
        if new_turn == "robot":
            threading.Timer(0.5, robot_play).start()

    return result

# ---------------------- ROBOT STRATEGY ----------------------
def robot_play(debug=False):
    """Robot’s turn: try confident match, else flip unseen, else fallback."""
    print("[ROBOT PLAY] Starting robot strategy...")
    # 1) Confident match
    unmatched = [sq for sq,data in memory_board.items() if not data["matched"]]
    for i in range(len(unmatched)):
        for j in range(i+1, len(unmatched)):
            a, b = unmatched[i], unmatched[j]
            if is_match(memory_board[a]["mean"], memory_board[a]["desc"],
                        memory_board[b]["mean"], memory_board[b]["desc"]):
                print(f"[ROBOT PLAY] Confident match: {a},{b}")
                log_move("robot_matched_pair",(a,b))
                square_queue.put(a); time.sleep(0.5); square_queue.put(b)
                return

    # 2) Flip a random unseen
    all_sq = [r+c for r in "ABCD" for c in "12345"]
    unseen = [s for s in all_sq if s not in memory_board]
    if unseen:
        pick1 = random.choice(unseen)
        print(f"[ROBOT PLAY] Flipping unseen: {pick1}")
        log_move("robot_flip", pick1)
        square_queue.put(pick1)

        # wait for it to register
        start = time.time()
        while pick1 not in memory_board and time.time() - start < 5.0:
            time.sleep(0.05)

        # try a match
        for s,data in memory_board.items():
            if s == pick1 or data["matched"]:
                continue
            if is_match(memory_board[pick1]["mean"], memory_board[pick1]["desc"],
                        data["mean"], data["desc"]):
                print(f"[ROBOT PLAY] Found match for {pick1}: {s}")
                log_move("robot_found_match",(pick1,s))
                square_queue.put(s)
                return

        # flip another unseen
        rest = [s for s in unseen if s != pick1]
        if rest:
            pick2 = random.choice(rest)
            print(f"[ROBOT PLAY] No match → flipping {pick2}")
            log_move("robot_second_flip", pick2)
            square_queue.put(pick2)
            return

    # 3) Fallback two random unmatched
    rem = [s for s,d in memory_board.items() if not d["matched"]]
    if len(rem) >= 2:
        a,b = random.sample(rem,2)
        print(f"[ROBOT PLAY] Fallback picks: {a},{b}")
        log_move("robot_fallback_pair",(a,b))
        square_queue.put(a); time.sleep(0.5); square_queue.put(b)
        return

    print("[ROBOT PLAY] No moves available.")

# ---------------------- HELPERS ----------------------
def check_match(m1, m2, d1, d2):
    vecs = np.array([m1, m2])
    pca  = PCA(n_components=min(PCA_DIMS, vecs.shape[0]))
    v3   = pca.fit_transform(vecs)
    dist = np.linalg.norm(v3[0] - v3[1])
    knn  = compute_knn_match_score(d1, d2)
    return (knn >= MATCH_KNN_SCORE_THRESHOLD or dist <= MATCH_DISTANCE_THRESHOLD), dist, knn

def is_match(m1, d1, m2, d2):
    return check_match(m1, m2, d1, d2)[0]

def switch_turn():
    global current_turn
    current_turn = "robot" if current_turn=="human" else "human"
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

def reset_game():
    global memory_board, matched_squares, current_turn, last_flipped, game_history
    memory_board.clear()
    matched_squares.clear()
    last_flipped.clear()
    game_history.clear()
    reset_turn_state()
    current_turn = "human"
    gui_queue.put({"status":"reset"})
    gui_queue.put({"event":"turn","player":"human"})

def get_turn():     return current_turn
def is_game_over(): return len(matched_squares) >= len(memory_board)
