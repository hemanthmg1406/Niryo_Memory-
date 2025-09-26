import sys, queue, pygame
from enum import Enum, auto
from typing import Dict, List, Optional
from memory_queues import square_queue, gui_queue

# ─────────────── 1. New Color Palette & Theme ───────────────
NIRYO_BLUE = (0, 150, 214)
NIRYO_LIGHT_BLUE = (50, 180, 230)
BACKGROUND_COLOR = (245, 245, 245)
CARD_BG = (255, 255, 255)
TEXT_DARK = (20, 30, 40)
TEXT_LIGHT = (100, 110, 120)
MATCH_BORDER = (255, 195, 18)  # Gold for match
MISMATCH_BORDER = (220, 80, 80) # Red for mismatch
BUTTON_SHADOW = (200, 200, 200)

# ─────────────── 2. New Dashboard-Style Layout ───────────────
WINDOW_W, WINDOW_H = 1280, 800
SIDEBAR_WIDTH = 320 # Space for the dashboard
GRID_PADDING = 40   # Padding around the card grid
BTN_W, BTN_H = 200, 50
ROWS, COLS = 4, 5
FPS = 60
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
game_phase = "playing"
winner_message = ""
FLIP_BACK_EVENT = pygame.USEREVENT + 1
squares_to_flip_back: List[str] = []

# ─────────────── Pygame Setup ───────────────
pygame.init()
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
pygame.display.set_caption("Niryo Memory Match – GUI")
clock = pygame.time.Clock()

# ─────────────── 3. Improved Typography ───────────────
try:
    font_main = pygame.font.SysFont("Arial", 24)
    font_title = pygame.font.SysFont("Arial", 36, bold=True)
    font_banner = pygame.font.SysFont("Arial", 48, bold=True)
except:
    font_main = pygame.font.SysFont("sans-serif", 24)
    font_title = pygame.font.SysFont("sans-serif", 36, bold=True)
    font_banner = pygame.font.SysFont("sans-serif", 48, bold=True)


MEMORY_BACK = pygame.image.load("memory.PNG").convert_alpha()

# --- Layout variables (will be calculated in reset_gui_state) ---
CELL_W, CELL_H = 0, 0
GRID_X, GRID_Y = 0, 0
btn_restart, btn_quit = pygame.Rect(0,0,0,0), pygame.Rect(0,0,0,0)
grid_rects: Dict[str, pygame.Rect] = {}

# ─────────────── Helper Functions ───────────────

def reset_gui_state():
    """Reset entire GUI state and recalc layout."""
    global score_human, score_robot, current_turn
    global cell_state, recent_clicks, cell_image, ICON_CACHE, squares_to_flip_back
    global game_phase, winner_message
    global CELL_W, CELL_H, GRID_X, GRID_Y
    global grid_rects, btn_restart, btn_quit

    game_phase, winner_message = "playing", ""
    score_human, score_robot, current_turn = 0, 0, "human"
    recent_clicks.clear()
    cell_image.clear()
    # ICON_CACHE is kept to avoid reloading images on restart
    squares_to_flip_back.clear()

    for sq in ALL_SQUARE_IDS:
        cell_state[sq] = CellState.BACK

    # --- New Layout Calculation for Dashboard ---
    grid_area_w = WINDOW_W - SIDEBAR_WIDTH - (GRID_PADDING * 2)
    grid_area_h = WINDOW_H - (GRID_PADDING * 2)

    cell_side = min(grid_area_w // COLS, grid_area_h // ROWS)
    CELL_W = CELL_H = cell_side
    
    grid_w = COLS * CELL_W
    grid_h = ROWS * CELL_H
    
    GRID_X = SIDEBAR_WIDTH + GRID_PADDING + (grid_area_w - grid_w) // 2
    GRID_Y = GRID_PADDING + (grid_area_h - grid_h) // 2

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
    
    # ─────────────── 5. Enhanced Buttons (Positioning) ───────────────
    btn_restart = pygame.Rect( (SIDEBAR_WIDTH - BTN_W) // 2, WINDOW_H - BTN_H - 100, BTN_W, BTN_H)
    btn_quit    = pygame.Rect(0,0,0,0) # Effectively hides the quit button

def hit_test(pos) -> Optional[str]:
    for lbl, rect in grid_rects.items():
        if rect.collidepoint(pos): return lbl
    return None

def draw_board(hover_lbl: Optional[str], mouse_pos):
    screen.fill(BACKGROUND_COLOR)

    # --- Draw Sidebar / Dashboard ---
    sidebar_rect = pygame.Rect(0, 0, SIDEBAR_WIDTH, WINDOW_H)
    pygame.draw.rect(screen, (255, 255, 255), sidebar_rect)
    pygame.draw.line(screen, (220, 220, 220), (SIDEBAR_WIDTH, 0), (SIDEBAR_WIDTH, WINDOW_H), 2)

    # Title
    title_surf = font_title.render("Niryo Memory", True, TEXT_DARK)
    screen.blit(title_surf, ( (SIDEBAR_WIDTH - title_surf.get_width()) // 2, 40) )
    
    # Turn Indicator
    banner = "Your Turn" if current_turn=="human" else "Robot's Turn"
    banner_surf = font_banner.render(banner, True, NIRYO_BLUE)
    screen.blit(banner_surf, ( (SIDEBAR_WIDTH - banner_surf.get_width()) // 2, 120) )
    
    # Scores
    score_y_start = 250
    human_score_surf = font_title.render(f"Human: {score_human}", True, TEXT_DARK)
    robot_score_surf = font_title.render(f"Robot: {score_robot}", True, TEXT_DARK)
    screen.blit(human_score_surf, ( (SIDEBAR_WIDTH - human_score_surf.get_width()) // 2, score_y_start) )
    screen.blit(robot_score_surf, ( (SIDEBAR_WIDTH - robot_score_surf.get_width()) // 2, score_y_start + 50) )


    # --- Draw Grid Cells ---
    for lbl, rect in grid_rects.items():
        state = cell_state[lbl]
        inner_rect = rect.inflate(-12, -12)

        # Draw card shadow and background
        pygame.draw.rect(screen, BUTTON_SHADOW, inner_rect.move(4, 4), border_radius=8)
        pygame.draw.rect(screen, CARD_BG, inner_rect, border_radius=8)

        if state == CellState.BACK:
            back_img = pygame.transform.smoothscale(MEMORY_BACK, (inner_rect.width, inner_rect.height))
            screen.blit(back_img, inner_rect.topleft)
            # Highlight if clicked
            if lbl in recent_clicks:
                pygame.draw.rect(screen, NIRYO_BLUE, inner_rect, 4, border_radius=8)
            # Tint on hover
            if lbl == hover_lbl:
                hover_surface = pygame.Surface(inner_rect.size, pygame.SRCALPHA)
                hover_surface.fill((255, 255, 255, 90))
                screen.blit(hover_surface, inner_rect.topleft)
        else:
            img = cell_image.get(lbl)
            if img:
                img_rect = img.get_rect(center=inner_rect.center)
                screen.blit(img, img_rect)
            
            # ─────────────── 4. Dynamic Effects (Enhanced Borders) ───────────────
            if state == CellState.MATCHED:
                pygame.draw.rect(screen, MATCH_BORDER, inner_rect, 5, border_radius=8)
            if lbl in squares_to_flip_back:
                pygame.draw.rect(screen, MISMATCH_BORDER, inner_rect, 5, border_radius=8)

    # --- 5. Enhanced Buttons (Drawing) ---
    for rect, label in ((btn_restart,"Restart Game"),):
        is_hovered = rect.collidepoint(mouse_pos)
        btn_color = NIRYO_LIGHT_BLUE if is_hovered else NIRYO_BLUE
        
        # Shadow
        pygame.draw.rect(screen, BUTTON_SHADOW, rect.move(4,4), border_radius=12)
        # Button
        pygame.draw.rect(screen, btn_color, rect, border_radius=12)
        
        text_surf = font_main.render(label, True, (255,255,255))
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)

def show_intro() -> None:
    # This function can also be updated with the new theme later if desired
    # For now, it remains functionally the same to ensure compatibility
    global difficulty
    btn_easy = pygame.Rect(WINDOW_W//2-300, WINDOW_H//2-25, 200,50)
    btn_med  = pygame.Rect(WINDOW_W//2- 50, WINDOW_H//2-25, 200,50)
    btn_hard = pygame.Rect(WINDOW_W//2+200, WINDOW_H//2-25, 200,50)
    title_s = font_banner.render("Welcome to Memory Match",True,NIRYO_BLUE)
    inst_s  = font_title.render("Select difficulty and start!",True,TEXT_DARK)
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
        
        screen.fill(BACKGROUND_COLOR)
        screen.blit(title_s, ( (WINDOW_W - title_s.get_width())//2, WINDOW_H//3-60) )
        screen.blit(inst_s, ( (WINDOW_W - inst_s.get_width())//2, WINDOW_H//3) )
        
        for btn,label in ((btn_easy,"Easy"),(btn_med,"Medium"),(btn_hard,"Hard")):
            clr = NIRYO_LIGHT_BLUE if btn.collidepoint(mp) else NIRYO_BLUE
            pygame.draw.rect(screen, clr, btn, border_radius=8)
            txt = font_main.render(label, True, (255,255,255))
            screen.blit(txt, txt.get_rect(center=btn.center))
        pygame.display.flip(); clock.tick(FPS)

def shutdown_program():
    screen.fill(BACKGROUND_COLOR)
    msg_surf = font_banner.render("Shutting down...", True, TEXT_DARK)
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

    if status == "reveal":
        sq, path = msg["square"], msg["image_path"]
        if cell_state.get(sq) != CellState.BACK:
            return
        if path not in ICON_CACHE:
            try:
                surf = pygame.image.load(path).convert_alpha()
                # Create a scaled surface and store it in the cache
                ICON_CACHE[path] = pygame.transform.smoothscale(surf, (CELL_W-24, CELL_H-24))
            except Exception as e:
                print(f"Error loading image {path}: {e}")
                pass # Prevent crash if image is missing/corrupt
        cell_state[sq] = CellState.FACE_UP
        cell_image[sq] = ICON_CACHE.get(path)

    elif status == "matched":
        for sq in msg.get("squares", []):
            cell_state[sq] = CellState.MATCHED
        recent_clicks.clear()

    elif status in ("mismatch", "flip_back"):
        squares_to_flip_back = msg.get("squares",[])[:]
        pygame.time.set_timer(FLIP_BACK_EVENT, 2000, loops=1) # slightly shorter wait time

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
            is_clickable = hover_lbl and cell_state.get(hover_lbl) == CellState.BACK
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if is_clickable else pygame.SYSTEM_CURSOR_ARROW)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                shutdown_program()

            if game_phase == "playing":
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if btn_quit.collidepoint(mouse_pos):
                        shutdown_program()

                    elif btn_restart.collidepoint(mouse_pos):
                        # Clear queues and reset GUI
                        try:
                            while True: square_queue.get_nowait()
                        except queue.Empty: pass
                        try:
                            while True: gui_queue.get_nowait()
                        except queue.Empty: pass
                        square_queue.put("reset_game") # Send reset command via square_queue


                    elif current_turn == "human" and hover_lbl and len(recent_clicks) < 2:
                        if hover_lbl not in recent_clicks:
                            square_queue.put(hover_lbl)
                            recent_clicks.append(hover_lbl)

                elif ev.type == FLIP_BACK_EVENT:
                    for sq in squares_to_flip_back:
                        cell_state[sq] = CellState.BACK
                    squares_to_flip_back.clear()
                    recent_clicks.clear()
                    # The logic module will now send the next turn event
            
            elif game_phase == "game_over":
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if btn_restart.collidepoint(mouse_pos):
                        gui_queue.put({"status":"reset"})
                        reset_gui_state()

        draw_board(hover_lbl, mouse_pos)
        if game_phase == "game_over":
            # Draw a semi-transparent overlay
            overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 200))
            screen.blit(overlay, (0,0))
            
            wm_surf = font_banner.render(winner_message, True, TEXT_DARK)
            wm_rect = wm_surf.get_rect(center=(WINDOW_W / 2, WINDOW_H / 2 - 50))
            screen.blit(wm_surf, wm_rect)

        pygame.display.flip()
        clock.tick(FPS)
        
    shutdown_program()

if __name__=="__main__":
    show_intro()
    run_gui()
