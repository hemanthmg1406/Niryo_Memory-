import sys, queue, pygame
from enum import Enum, auto
from typing import Dict, List, Optional
from memory_queues import square_queue, gui_queue

# ─────────────── Layout & Colours ───────────────
WINDOW_W, WINDOW_H = 1280, 800
ROWS, COLS = 4, 5
GRID_X0, GRID_Y0 = 120, 120
BTN_W, BTN_H = 180, 50
GRAD_TOP = (20, 24, 28)
GRAD_BOTTOM = (10, 12, 16)
CARD_BG = (30, 36, 44)
HOVER_TINT = (255, 255, 255, 160)
TEXT_MAIN = (240, 240, 240)
TEXT_ACCENT = (160, 160, 160)
ACCENT = (72, 212, 163)
MATCH_BORDER = (255, 195, 18)
MISMATCH_BORDER = (220, 80, 80)
BTN_NORMAL = ACCENT
BTN_HOVER = (98, 240, 190)
FPS = 60
LABEL_SPACE = 50
ALL_SQUARE_IDS = [r + c for r in "ABCD" for c in "12345"]

class CellState(Enum):
    BACK = auto()
    FACE_UP = auto()
    MATCHED = auto()

# --- Core State Variables ---
cell_state: Dict[str, CellState] = {}
cell_image: Dict[str, pygame.Surface] = {}
ICON_CACHE: Dict[str, pygame.Surface] = {}
score_human, score_robot = 0, 0
current_turn = "human"
recent_clicks: List[str] = []

# --- State Machine & Timer ---
game_phase = "playing"  # "playing" or "game_over"
winner_message = ""
FLIP_BACK_EVENT = pygame.USEREVENT + 1
squares_to_flip_back: List[str] = []

# ─────────────── Pygame Setup ───────────────
pygame.init()
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
pygame.display.set_caption("Niryo Memory Match – GUI")
clock = pygame.time.Clock()
font_small  = pygame.font.SysFont("Segoe UI", 24)
font_medium = pygame.font.SysFont("Segoe UI", 32)
font_banner = pygame.font.SysFont("Segoe UI Semibold", 64)

# Load the card-back image (must exist alongside this script)
MEMORY_BACK = pygame.image.load("memory.PNG").convert_alpha()

CELL_W, CELL_H = 0, 0
GRID_W, GRID_H = 0, 0
GRID_X, GRID_Y = GRID_X0, GRID_Y0
btn_restart, btn_quit = pygame.Rect(0,0,0,0), pygame.Rect(0,0,0,0)
grid_rects: Dict[str, pygame.Rect] = {}

# ─────────────── Helper Functions ───────────────

def reset_gui_state():
    """Reset entire GUI state and recalc layout."""
    global score_human, score_robot, current_turn
    global cell_state, recent_clicks, cell_image, ICON_CACHE, squares_to_flip_back
    global game_phase, winner_message
    global CELL_W, CELL_H, GRID_W, GRID_H, GRID_X, GRID_Y
    global grid_rects, btn_restart, btn_quit

    game_phase, winner_message = "playing", ""
    score_human, score_robot, current_turn = 0, 0, "human"
    recent_clicks.clear()
    cell_image.clear()
    ICON_CACHE.clear()
    squares_to_flip_back.clear()

    for sq in ALL_SQUARE_IDS:
        cell_state[sq] = CellState.BACK

    # --- Updated Layout Calculation ---
    # This block is modified to create space for the labels on the left and bottom.
    # It assumes a global constant `LABEL_SPACE` is defined (e.g., LABEL_SPACE = 50).
    
    # 1. Reduce the available area to make room for labels.
    avail_w = WINDOW_W - 2 * GRID_X0 - LABEL_SPACE
    avail_h = WINDOW_H - 300 - LABEL_SPACE

    # 2. Calculate card and grid size based on the smaller available area.
    cell_side = min(avail_w // COLS, avail_h // ROWS)
    CELL_W = CELL_H = cell_side
    GRID_W = COLS * CELL_W
    GRID_H = ROWS * CELL_H

    # 3. Center the card grid within the new, smaller available space.
    offset_x = (avail_w - GRID_W) // 2
    offset_y = (avail_h - GRID_H) // 2

    # 4. Set the final grid position, adding the LABEL_SPACE on the left.
    GRID_X = GRID_X0 + LABEL_SPACE + offset_x
    GRID_Y = GRID_Y0 + offset_y
    # --- End of Updated Block ---

    grid_rects.clear()
    for r in range(ROWS):
        for c in range(COLS):
            lbl = f"{chr(65+r)}{c+1}"
            rect = pygame.Rect(
                GRID_X + c*CELL_W,
                GRID_Y + r*CELL_H,
                CELL_W, CELL_H
            )
            grid_rects[lbl] = rect

    btn_restart = pygame.Rect(WINDOW_W//2 - BTN_W - 30, WINDOW_H - 80, BTN_W, BTN_H)
    btn_quit    = pygame.Rect(WINDOW_W//2 +  30, WINDOW_H - 80, BTN_W, BTN_H)
def draw_gradient(surface, top, bottom):
    h = surface.get_height()
    for y in range(h):
        ratio = y / h
        c = (
            int(top[0]*(1-ratio) + bottom[0]*ratio),
            int(top[1]*(1-ratio) + bottom[1]*ratio),
            int(top[2]*(1-ratio) + bottom[2]*ratio)
        )
        pygame.draw.line(surface, c, (0,y), (surface.get_width(),y))

def hit_test(pos) -> Optional[str]:
    for lbl, rect in grid_rects.items():
        if rect.collidepoint(pos): return lbl
    return None

def draw_board(hover_lbl: Optional[str], mouse_pos):
    draw_gradient(screen, GRAD_TOP, GRAD_BOTTOM)
    banner = "Your turn" if current_turn=="human" else "Robot's turn"
    bs = font_banner.render(banner, True, ACCENT)
    screen.blit(bs, (WINDOW_W//2 - bs.get_width()//2, 20))

    # --- New code to draw row and column labels ---
    for r in range(ROWS):
        label_surf = font_medium.render(chr(ord('A') + r), True, TEXT_ACCENT)
        # Position the label in the middle of the reserved space on the left
        cx = GRID_X - LABEL_SPACE // 2
        cy = GRID_Y + r * CELL_H + CELL_H // 2
        label_rect = label_surf.get_rect(center=(cx, cy))
        screen.blit(label_surf, label_rect)

    for c in range(COLS):
        label_surf = font_medium.render(str(c + 1), True, TEXT_ACCENT)
        # Position the label in the middle of the reserved space on the bottom
        cx = GRID_X + c * CELL_W + CELL_W // 2
        cy = GRID_Y + GRID_H + LABEL_SPACE // 2
        label_rect = label_surf.get_rect(center=(cx, cy))
        screen.blit(label_surf, label_rect)
    # --- End of new code ---
    
    msg_x, msg_y = GRID_X + GRID_W + 30, GRID_Y
    for i, lbl in enumerate(recent_clicks):
        surf = font_medium.render(f"Card {lbl} selected", True, TEXT_MAIN)
        screen.blit(surf, (msg_x, msg_y + i * (surf.get_height() + 5)))

    # Grid cells
    for lbl, rect in grid_rects.items():
        state = cell_state[lbl]
        inner = rect.inflate(-12, -12)

        # draw card BACK as MEMORY_BACK or solid
        if state == CellState.BACK:
            back = pygame.transform.smoothscale(MEMORY_BACK, (inner.width, inner.height))
            screen.blit(back, inner.topleft)
            # highlight if clicked
            if lbl in recent_clicks:
                pygame.draw.rect(screen, ACCENT, inner, 4)
            # tint on hover
            if lbl == hover_lbl:
                ov = pygame.Surface((inner.width,inner.height), pygame.SRCALPHA)
                ov.fill(HOVER_TINT)
                screen.blit(ov, inner.topleft)
        else:
            # face up or matched
            img = cell_image.get(lbl)
            if img:
                screen.blit(img, img.get_rect(center=inner.center))
            # matched border
            if state == CellState.MATCHED:
                #print(f"Drawing MATCHED border for {lbl}")
                pygame.draw.rect(screen, MATCH_BORDER, inner, 4)
            # mismatched highlight
            if lbl in squares_to_flip_back:
                pygame.draw.rect(screen, MISMATCH_BORDER, inner, 4)

    # Scores
    sh = font_small.render(f"HUMAN: {score_human}", True, TEXT_MAIN)
    sr = font_small.render(f"ROBOT: {score_robot}", True, TEXT_MAIN)
    screen.blit(sh, (40, WINDOW_H-120))
    screen.blit(sr, (WINDOW_W-200, WINDOW_H-120))

    # Buttons
    for rect, label in ((btn_restart,"Restart Game"), (btn_quit,"Quit Game")):
        col = BTN_HOVER if rect.collidepoint(mouse_pos) else BTN_NORMAL
        pygame.draw.rect(screen, col, rect, border_radius=8)
        ts = font_small.render(label, True, (30,30,30))
        screen.blit(ts, (rect.centerx - ts.get_width()//2, rect.centery - ts.get_height()//2))
def show_intro() -> None:
    global difficulty
    btn_easy = pygame.Rect(WINDOW_W//2-300, WINDOW_H//2-25, 200,50)
    btn_med  = pygame.Rect(WINDOW_W//2- 50, WINDOW_H//2-25, 200,50)
    btn_hard = pygame.Rect(WINDOW_W//2+200, WINDOW_H//2-25, 200,50)
    title_f = pygame.font.SysFont("Segoe UI Semibold",48)
    inst_f  = pygame.font.SysFont("Segoe UI",28)
    title_s = title_f.render("Welcome to Memory Match",True,ACCENT)
    inst_s  = inst_f.render("Select difficulty and start!",True,TEXT_MAIN)
    difficulty=None
    while difficulty is None:
        mp = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT:
                shutdown_program()
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                if btn_easy.collidepoint(mp): difficulty="easy"
                elif btn_med.collidepoint(mp): difficulty="medium"
                elif btn_hard.collidepoint(mp): difficulty="hard"
        draw_gradient(screen,GRAD_TOP,GRAD_BOTTOM)
        screen.blit(title_s, (WINDOW_W//2-title_s.get_width()//2, WINDOW_H//3-60))
        screen.blit(inst_s, (WINDOW_W//2-inst_s.get_width()//2, WINDOW_H//3))
        for btn,label in ((btn_easy,"Easy"),(btn_med,"Medium"),(btn_hard,"Hard")):
            clr = BTN_HOVER if btn.collidepoint(mp) else BTN_NORMAL
            pygame.draw.rect(screen, clr, btn, border_radius=8)
            txt = inst_f.render(label, True, (30,30,30))
            screen.blit(txt,(btn.centerx-txt.get_width()//2, btn.centery-txt.get_height()//2))
        pygame.display.flip(); clock.tick(FPS)

def shutdown_program():
    screen.fill(GRAD_BOTTOM)
    msg_font = pygame.font.SysFont("Segoe UI", 48)
    msg_surf = msg_font.render("Shutting down...", True, TEXT_MAIN)
    msg_rect = msg_surf.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2))
    screen.blit(msg_surf, msg_rect)
    pygame.display.flip()
    pygame.time.wait(1200)
    pygame.quit()
    sys.exit()

def handle_robot_msg(msg: dict) -> None:
    global game_phase, winner_message
    global current_turn, score_human, score_robot, squares_to_flip_back
    status, event = msg.get("status"), msg.get("event")
    #print(f"[GUI] Received from gui_queue @ {time.time()}: {event} ({status})")
    #print(f"[GUI] Status: {status}, Event: {event}")

    if status == "reveal":
            sq, path = msg["square"], msg["image_path"]

            # --- ADD THIS CHECK ---
            # Only reveal a card if it is still face-down.
            # This prevents a 'reveal' message from overwriting a 'matched' state.
            if cell_state.get(sq) != CellState.BACK:
                return # Or continue, if this is in a loop processing multiple messages

            if path not in ICON_CACHE:
                try:
                    surf = pygame.image.load(path).convert_alpha()
                    ICON_CACHE[path] = pygame.transform.smoothscale(surf, (CELL_W-6, CELL_H-6))
                except:
                    pass
            cell_state[sq] = CellState.FACE_UP
            cell_image[sq] = ICON_CACHE.get(path)

    elif status == "matched":
        print(f"Matched message received: {msg}")
        print(f"squares list: {msg.get('squares', [])}, length={len(msg.get('squares', []))}")
        for sq in msg.get("squares", []):
            print(f"--> About to mark {sq}")
            cell_state[sq] = CellState.MATCHED
            print(f"Marked {sq} as MATCHED")
        recent_clicks.clear()


    elif status in ("mismatch", "flip_back"):
        squares_to_flip_back = msg.get("squares",[])[:]
        pygame.time.set_timer(FLIP_BACK_EVENT, 3000, loops=1)


    elif status == "reset":
        reset_gui_state()

    if event == "turn":
        current_turn = msg.get("player")
    elif event == "score":
        score_human = msg.get("human_score", score_human)
        score_robot = msg.get("robot_score", score_robot)
    elif event == "game_over":
        game_phase = "game_over"
        winner_message = f"{msg['winner']} wins! {msg['human_score']}–{msg['robot_score']}"

def run_gui() -> None:
    global recent_clicks, game_phase
    hover_lbl = None
    reset_gui_state()
    running = True

    while running:
        try:
            while True: handle_robot_msg(gui_queue.get_nowait())
        except queue.Empty:
            pass
            
        mouse_pos = pygame.mouse.get_pos()
        new_hover = hit_test(mouse_pos)
        if new_hover != hover_lbl:
            hover_lbl = new_hover
            if hover_lbl and cell_state[hover_lbl] == CellState.BACK:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            else:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                shutdown_program()

            if game_phase == "playing":
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if btn_quit.collidepoint(mouse_pos):
                        shutdown_program()

                    elif btn_restart.collidepoint(mouse_pos):
                        reset_gui_state()
                        try:
                            while True: square_queue.get_nowait()
                        except queue.Empty:
                            pass
                        try:
                            while True: gui_queue.get_nowait()
                        except queue.Empty:
                            pass
                        gui_queue.put({"event": "turn", "player": "human"})

                    elif current_turn == "human" and hover_lbl and len(recent_clicks) < 2:
                        square_queue.put(hover_lbl)
                        recent_clicks.append(hover_lbl)

                elif ev.type == FLIP_BACK_EVENT:
                    for sq in squares_to_flip_back:
                        cell_state[sq] = CellState.BACK
                    squares_to_flip_back.clear()
                    recent_clicks.clear()
                    gui_queue.put({"event": "turn", "player": current_turn})

            elif game_phase == "game_over":
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if btn_restart.collidepoint(mouse_pos):
                        gui_queue.put({"event":"reset"})
                    if btn_quit.collidepoint(mouse_pos):
                        shutdown_program()

        draw_board(hover_lbl, mouse_pos)
        if game_phase == "game_over":
            wm = font_banner.render(winner_message, True, MATCH_BORDER)
            screen.blit(wm, (WINDOW_W//2 - wm.get_width()//2, GRID_Y//2))

        pygame.display.flip()
        clock.tick(FPS)
        
    shutdown_program()

if __name__=="__main__":
    show_intro()
    run_gui()
