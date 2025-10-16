import sys, queue, pygame, random
from enum import Enum, auto
from typing import Dict, List, Optional
from memory_queues import square_queue, gui_queue
from user_feedback import play_sound

# ─────────────── 1. New Color Palette & Theme ───────────────
NIRYO_BLUE = (0, 150, 214)
NIRYO_LIGHT_BLUE = (50, 180, 230)
BACKGROUND_COLOR = (245, 245, 245)
CARD_BG = (255, 255, 255)
TEXT_DARK = (20, 30, 40)
TEXT_LIGHT = (100, 110, 120)
MATCH_BORDER = (46, 204, 113)  # Gold for match
MISMATCH_BORDER = (220, 80, 80) # Red for mismatch
BUTTON_SHADOW = (200, 200, 200)

# --- NEW: Added new button colors ---
BTN_EASY_COLOR = (46, 204, 113)      # Green
BTN_EASY_HOVER = (88, 214, 141)
BTN_MEDIUM_COLOR = (241, 196, 15)    # Yellow
BTN_MEDIUM_HOVER = (244, 208, 63)
BTN_HARD_COLOR = (155, 89, 182)      # Purple
BTN_HARD_HOVER = (175, 122, 197)


# ─────────────── 2. New Dashboard-Style Layout ───────────────
WINDOW_W, WINDOW_H = 1280, 800 # Default window size
SIDEBAR_WIDTH = 320 # Space for the dashboard
GRID_PADDING = 40   # Padding around the card grid
BTN_W, BTN_H = 200, 50
ROWS, COLS = 4, 5
FPS = 60
HINT_FLASH_END = pygame.USEREVENT + 3 # Choose a new unique event ID
MESSAGE_TIMER_EVENT = pygame.USEREVENT + 4 # New unique event ID
ROBOT_STATUS_EVENT = pygame.USEREVENT + 5
btn_hint = pygame.Rect(0,0,0,0) # Define globally
temporary_message = "" # Stores the message text
robot_status_message = ""
RESET_DESTINATION = "game" # Default reset destination

# Define the button rect near the bottom of the sidebar
# Place it above the Restart and Back buttons
BTN_W, BTN_H = 200, 50
# ... (near btn_restart and btn_back definitions)

# Place the Hint button slightly higher than the existing buttons
btn_hint = pygame.Rect( (SIDEBAR_WIDTH - BTN_W) // 2, WINDOW_H - BTN_H - 240, BTN_W, BTN_H)
ALL_SQUARE_IDS = [r + c for r in "ABCD" for c in "12345"]

class CellState(Enum):
    BACK = auto()
    FACE_UP = auto()
    MATCHED = auto()

class Confetti:
    def __init__(self, x, y, x_vel, y_vel, color):
        self.x = x
        self.y = y
        self.x_vel = x_vel
        self.y_vel = y_vel
        self.color = color
        self.radius = random.randint(2, 4)

    def update(self):
        self.x += self.x_vel
        self.y += self.y_vel
        self.y_vel += 0.1  # Gravity

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

confetti_particles = []


# --- Core State Variables ---
cell_state: Dict[str, CellState] = {}
cell_image: Dict[str, pygame.Surface] = {}
ICON_CACHE: Dict[str, pygame.Surface] = {}
score_human, score_robot = 0, 0
current_turn = "human"
recent_clicks: List[str] = []
player_name = "Player" # Default name
difficulty = "hard" # Global variable for difficulty
audio_profile = "adult"

# --- Typewriter Animation State ---
animation_states = {}
TYPEWRITER_SPEED = 50  # Milliseconds per character

# --- State Machine & Timer ---
game_phase = "playing"
winner_message = ""
FLIP_BACK_EVENT = pygame.USEREVENT + 1
INTRO_SOUND_EVENT = pygame.USEREVENT + 2
SELECT_LEVEL_SOUND_EVENT = pygame.USEREVENT + 3
squares_to_flip_back: List[str] = []

# ─────────────── Pygame Setup ───────────────
pygame.init()
pygame.mixer.init()

# --- MODIFICATION FOR RESIZABLE WINDOW ---
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE)

pygame.display.set_caption("Niryo Memory Match – GUI")
clock = pygame.time.Clock()

# ─────────────── 3. Improved Typography ───────────────
try:
    font_main = pygame.font.SysFont("Arial", 24)
    font_title = pygame.font.SysFont("Arial", 36, bold=True)
    font_banner = pygame.font.SysFont("Arial", 48, bold=True)
    font_status = pygame.font.SysFont("Arial", 32, bold=True)
except:
    font_main = pygame.font.SysFont("sans-serif", 24)
    font_title = pygame.font.SysFont("sans-serif", 36, bold=True)
    font_banner = pygame.font.SysFont("sans-serif", 48, bold=True)
    font_status = pygame.font.SysFont("sans-serif", 32, bold=True)

MEMORY_BACK = pygame.image.load("memory.PNG").convert_alpha()

# --- Layout variables (will be calculated in reset_gui_state) ---
CELL_W, CELL_H = 0, 0
GRID_X, GRID_Y = 0, 0
btn_restart, btn_quit, btn_back = pygame.Rect(0,0,0,0), pygame.Rect(0,0,0,0), pygame.Rect(0,0,0,0)
grid_rects: Dict[str, pygame.Rect] = {}

# ─────────────── Animation Helper Functions ───────────────

def start_typewriter_animation(key, text):
    global animation_states
    animation_states[key] = {
        'full_text': text,
        'visible_chars': 0,
        'last_update': pygame.time.get_ticks(),
        'visible_text': ''
    }

def update_typewriter_animations():
    global animation_states
    now = pygame.time.get_ticks()
    for state in animation_states.values():
        full_text = state['full_text']
        if state['visible_chars'] < len(full_text):
            if now - state['last_update'] > TYPEWRITER_SPEED:
                state['visible_chars'] += 1
                state['last_update'] = now
        state['visible_text'] = full_text[:state['visible_chars']]

# ─────────────── Helper Functions ───────────────

def reset_gui_state():
    """Reset entire GUI state and recalc layout."""
    global score_human, score_robot, current_turn
    global cell_state, recent_clicks, cell_image, ICON_CACHE, squares_to_flip_back
    global game_phase, winner_message
    global CELL_W, CELL_H, GRID_X, GRID_Y
    global grid_rects, btn_restart, btn_quit, btn_back, WINDOW_W, WINDOW_H
    global robot_status_message
    global RESET_DESTINATION
    

    

    # Update window dimensions in case of resize
    WINDOW_W, WINDOW_H = screen.get_width(), screen.get_height()
    robot_status_message = ""

    game_phase, winner_message = "playing", ""
    score_human, score_robot, current_turn = 0, 0, "human"
    recent_clicks.clear()
    cell_image.clear()
    ICON_CACHE.clear() # Clear the icon cache to force recreation of scaled images
    squares_to_flip_back.clear()

    start_typewriter_animation("robot_status", "System Ready")
    start_typewriter_animation("title", "Niryo Memory")
    start_typewriter_animation("banner", "Your Turn")
    start_typewriter_animation("score_human", f"{player_name}: {score_human}")
    start_typewriter_animation("score_robot", f"Robot: {score_robot}")
    start_typewriter_animation("difficulty", f"Level: {difficulty.capitalize()}")

    for sq in ALL_SQUARE_IDS:
        # 1. Flip all non-matched cards back to BACK state
        if cell_state.get(sq) != CellState.MATCHED:
            cell_state[sq] = CellState.BACK 
        
        # 2. Clear any images that were revealed
        if sq in cell_image:
            del cell_image[sq]

    for sq in ALL_SQUARE_IDS:
        cell_state[sq] = CellState.BACK

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
            rect = pygame.Rect(GRID_X + c*CELL_W, GRID_Y + r*CELL_H, CELL_W, CELL_H)
            grid_rects[lbl] = rect

    btn_restart = pygame.Rect( (SIDEBAR_WIDTH - BTN_W) // 2, WINDOW_H - BTN_H - 100, BTN_W, BTN_H)
    btn_back = pygame.Rect( (SIDEBAR_WIDTH - BTN_W) // 2, WINDOW_H - BTN_H - 170, BTN_W, BTN_H)
    btn_quit    = pygame.Rect(0,0,0,0)
    RESET_DESTINATION = "game" 

def hit_test(pos) -> Optional[str]:
    for lbl, rect in grid_rects.items():
        if rect.collidepoint(pos): return lbl
    return None

def draw_board(hover_lbl: Optional[str], mouse_pos):
    # Ensure temporary_message is declared globally in the file
    global difficulty, temporary_message
    
    screen.fill(BACKGROUND_COLOR)

    sidebar_rect = pygame.Rect(0, 0, SIDEBAR_WIDTH, WINDOW_H)
    pygame.draw.rect(screen, (255, 255, 255), sidebar_rect)
    pygame.draw.line(screen, (220, 220, 220), (SIDEBAR_WIDTH, 0), (SIDEBAR_WIDTH, WINDOW_H), 2)

    title_text = animation_states.get("title", {}).get("visible_text", "")
    banner_text = animation_states.get("banner", {}).get("visible_text", "")
    sh_text = animation_states.get("score_human", {}).get("visible_text", "")
    sr_text = animation_states.get("score_robot", {}).get("visible_text", "")
    diff_text = animation_states.get("difficulty", {}).get("visible_text", "")

    title_surf = font_title.render(title_text, True, TEXT_DARK)
    screen.blit(title_surf, ( (SIDEBAR_WIDTH - title_surf.get_width()) // 2, 50) )

    banner_surf = font_banner.render(banner_text, True, NIRYO_BLUE)
    screen.blit(banner_surf, ( (SIDEBAR_WIDTH - banner_surf.get_width()) // 2, 150) )

    score_y_start = 290
    human_score_surf = font_title.render(sh_text, True, TEXT_DARK)
    robot_score_surf = font_title.render(sr_text, True, TEXT_DARK)
    screen.blit(human_score_surf, ( (SIDEBAR_WIDTH - human_score_surf.get_width()) // 2, score_y_start) )
    screen.blit(robot_score_surf, ( (SIDEBAR_WIDTH - robot_score_surf.get_width()) // 2, score_y_start + 60) )

    diff_surf = font_main.render(diff_text, True, TEXT_LIGHT)
    screen.blit(diff_surf, ( (SIDEBAR_WIDTH - diff_surf.get_width()) // 2, score_y_start + 120) )
    status_text = animation_states.get("robot_status", {}).get("visible_text", "")
    STATUS_COLOR=(0,180,180)
    status_surf = font_status.render(status_text, True, STATUS_COLOR) # Use NIRYO_BLUE for a clear status
    
    # Position the status below difficulty, centered
    status_y_start = score_y_start + 180 
    screen.blit(status_surf, ( (SIDEBAR_WIDTH - status_surf.get_width()) // 2, status_y_start) )
    # --- END NEW DRAW ---
    
    # --- DRAW HINT BUTTON ---
    if difficulty == "easy":
        rect = btn_hint
        label = "Hint"
        
        # Check hover state
        is_hovered = rect.collidepoint(mouse_pos)
        # Using a distinct color for the Hint (Greenish)
        btn_color = NIRYO_LIGHT_BLUE if is_hovered else (80, 200, 80)
        
        pygame.draw.rect(screen, BUTTON_SHADOW, rect.move(4,4), border_radius=12)
        pygame.draw.rect(screen, btn_color, rect, border_radius=12)
        
        text_surf = font_main.render(label, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)

    # --- DRAW GAME GRID AND CARDS ---
    for lbl, rect in grid_rects.items():
        state = cell_state[lbl]
        inner_rect = rect.inflate(-12, -12)
        pygame.draw.rect(screen, BUTTON_SHADOW, inner_rect.move(4, 4), border_radius=8)
        pygame.draw.rect(screen, CARD_BG, inner_rect, border_radius=8)

        if state == CellState.BACK:
            back_img = pygame.transform.smoothscale(MEMORY_BACK, (inner_rect.width, inner_rect.height))
            screen.blit(back_img, inner_rect.topleft)
            if lbl in recent_clicks:
                pygame.draw.rect(screen, NIRYO_BLUE, inner_rect, 4, border_radius=8)
            if lbl == hover_lbl:
                hover_surface = pygame.Surface(inner_rect.size, pygame.SRCALPHA)
                hover_surface.fill((255, 255, 255, 90))
                screen.blit(hover_surface, inner_rect.topleft)
        else:
            img = cell_image.get(lbl)
            if img:
                img_rect = img.get_rect(center=inner_rect.center)
                screen.blit(img, img_rect)

            if state == CellState.MATCHED:
                pygame.draw.rect(screen, MATCH_BORDER, inner_rect, 5, border_radius=8)
            if lbl in squares_to_flip_back:
                pygame.draw.rect(screen, MISMATCH_BORDER, inner_rect, 5, border_radius=8)

    # --- DRAW RESTART/BACK BUTTONS ---
    for rect, label in ((btn_restart,"Restart Game"), (btn_back, "Back")):
        is_hovered = rect.collidepoint(mouse_pos)
        btn_color = NIRYO_LIGHT_BLUE if is_hovered else NIRYO_BLUE
        pygame.draw.rect(screen, BUTTON_SHADOW, rect.move(4,4), border_radius=12)
        pygame.draw.rect(screen, btn_color, rect, border_radius=12)
        text_surf = font_main.render(label, True, (255,255,255))
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)
        
    # ----------------------------------------------------
    # --- NEW: DRAW TEMPORARY SCREEN MESSAGE OVER EVERYTHING ---
    # ----------------------------------------------------
    if temporary_message:
        # Create a translucent overlay
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        # Use semi-transparent black for the background of the message
        overlay.fill((0, 0, 0, 100))
        
        # Render the message text (use font_banner for prominence)
        # NOTE: temporary_message must be a global variable in game_gui.py
        msg_surf = font_banner.render(temporary_message, True, (255, 255, 255))
        msg_rect = msg_surf.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2))
        
        # Draw overlay and text
        screen.blit(overlay, (0,0))
        screen.blit(msg_surf, msg_rect)

def show_intro() -> None:
    global difficulty, player_name, audio_profile, screen, WINDOW_W, WINDOW_H
    user_name = ""
    input_box = pygame.Rect(WINDOW_W // 2 - 150, WINDOW_H // 3 + 80, 300, 50)
    color_inactive = NIRYO_BLUE
    color_active = TEXT_DARK
    color = color_inactive
    active = False
    name_entered = False
    profile_selected = False

    btn_adult = pygame.Rect(WINDOW_W // 2 - 225, WINDOW_H // 2 + 50, 200, 50)
    btn_kid = pygame.Rect(WINDOW_W // 2 + 25, WINDOW_H // 2 + 50, 200, 50)

    btn_easy = pygame.Rect(WINDOW_W//2-350, WINDOW_H//2+50, 200, 50)
    btn_med  = pygame.Rect(WINDOW_W//2-100, WINDOW_H//2+50, 200, 50)
    btn_hard = pygame.Rect(WINDOW_W//2+150, WINDOW_H//2+50, 200, 50)

    btn_place_cards = pygame.Rect(WINDOW_W//2 - 225, WINDOW_H//2 + 120, 200, 50)
    btn_collect_cards = pygame.Rect(WINDOW_W//2 + 25, WINDOW_H//2 + 120, 200, 50)

    title_full_text = "Welcome to Memory Match"
    instruction_text = "Enter your name:"
    title_visible_chars = 0
    inst_visible_chars = 0
    last_update = pygame.time.get_ticks()
    cursor_visible = True
    last_cursor_toggle = pygame.time.get_ticks()

    difficulty_selection = None
    play_select_level_sound = True

    intro_running = True
    while intro_running:
        mp = pygame.mouse.get_pos()

        is_hovering_button = (
            (name_entered and not profile_selected and (btn_adult.collidepoint(mp) or btn_kid.collidepoint(mp))) or
            (profile_selected and (btn_easy.collidepoint(mp) or btn_med.collidepoint(mp) or btn_hard.collidepoint(mp) or
                                   btn_place_cards.collidepoint(mp) or btn_collect_cards.collidepoint(mp)))
        )
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if is_hovering_button else pygame.SYSTEM_CURSOR_ARROW)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                shutdown_program()

            elif ev.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
                WINDOW_W, WINDOW_H = screen.get_width(), screen.get_height()
                # Recalculate button positions after resize
                input_box = pygame.Rect(WINDOW_W // 2 - 150, WINDOW_H // 3 + 80, 300, 50)
                btn_adult = pygame.Rect(WINDOW_W // 2 - 225, WINDOW_H // 2 + 50, 200, 50)
                btn_kid = pygame.Rect(WINDOW_W // 2 + 25, WINDOW_H // 2 + 50, 200, 50)
                btn_easy = pygame.Rect(WINDOW_W//2-350, WINDOW_H//2+50, 200, 50)
                btn_med  = pygame.Rect(WINDOW_W//2-100, WINDOW_H//2+50, 200, 50)
                btn_hard = pygame.Rect(WINDOW_W//2+150, WINDOW_H//2+50, 200, 50)
                btn_place_cards = pygame.Rect(WINDOW_W//2 - 225, WINDOW_H//2 + 120, 200, 50)
                btn_collect_cards = pygame.Rect(WINDOW_W//2 + 25, WINDOW_H//2 + 120, 200, 50)


            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_q:
                    shutdown_program()
                if active:
                    if ev.key == pygame.K_RETURN:
                        if user_name:
                            player_name = user_name
                            name_entered = True
                            active = False
                            instruction_text = "Are you an adult or a kid?"
                            if play_select_level_sound:
                                pygame.time.set_timer(SELECT_LEVEL_SOUND_EVENT, 200, loops=1)
                                play_select_level_sound = False
                    elif ev.key == pygame.K_BACKSPACE:
                        user_name = user_name[:-1]
                    else:
                        if len(user_name) < 20:
                            user_name += ev.unicode

            if ev.type == INTRO_SOUND_EVENT:
                play_sound("intro")

            if ev.type == SELECT_LEVEL_SOUND_EVENT:
                play_sound("selectlevel")

            if ev.type == pygame.MOUSEBUTTONDOWN:
                if not name_entered:
                    if input_box.collidepoint(ev.pos):
                        active = not active
                    else:
                        active = False
                    color = color_active if active else color_inactive
                elif not profile_selected:
                    if btn_adult.collidepoint(mp):
                        audio_profile = "adult"
                        profile_selected = True
                        play_sound("adult/description_human")
                        instruction_text = f"Hello {player_name}, select difficulty or setup board:"
                    elif btn_kid.collidepoint(mp):
                        audio_profile = "kid"
                        profile_selected = True
                        play_sound("kid/description_kid")
                        instruction_text = f"Hello {player_name}, select difficulty or setup board:"
                elif ev.button == 1:
                    """
                    if btn_place_cards.collidepoint(mp):
                        print("[GUI] Place Cards button clicked. Sending command...")
                        square_queue.put({"event": "place_cards"})
                    elif btn_collect_cards.collidepoint(mp):
                        print("[GUI] Collect Cards button clicked. Sending command...")
                        square_queue.put({"event": "collect_cards"})
                        """
                    
                    if btn_easy.collidepoint(mp):
                        difficulty_selection = "easy"
                        if audio_profile == 'adult':
                            play_sound("adult/level_human/easy")
                        else:
                            play_sound("kid/level_kid/easy1")
                        intro_running = False
                    elif btn_med.collidepoint(mp):
                        difficulty_selection = "medium"
                        if audio_profile == 'adult':
                            play_sound("adult/level_human/medium")
                        else:
                            play_sound("kid/level_kid/medium1")
                        intro_running = False
                    elif btn_hard.collidepoint(mp):
                        difficulty_selection = "hard"
                        if audio_profile == 'adult':
                            play_sound("adult/level_human/hard")
                        else:
                            play_sound("kid/level_kid/hard1")
                        intro_running = False
                    elif difficulty == "easy":
                        if btn_hint.collidepoint(mp) and game_phase == "playing" and current_turn == "human":
                            # Send command to the logic thread to find a pair
                            square_queue.put({"event": "GET_HINT"})

        screen.fill(BACKGROUND_COLOR)

        now = pygame.time.get_ticks()
        if now - last_update > 40:
            if title_visible_chars < len(title_full_text):
                title_visible_chars += 1
            elif not name_entered and inst_visible_chars < len(instruction_text):
                 inst_visible_chars += 1
            last_update = now

        if now - last_cursor_toggle > 500:
            cursor_visible = not cursor_visible
            last_cursor_toggle = now

        title_s = font_banner.render(title_full_text[:title_visible_chars], True, NIRYO_BLUE)
        screen.blit(title_s, ( (WINDOW_W - title_s.get_width()) // 2, WINDOW_H // 3 - 80) )

        inst_s = font_title.render(instruction_text, True, TEXT_DARK)
        screen.blit(inst_s, ( (WINDOW_W - inst_s.get_width()) // 2, WINDOW_H // 3 + 10) )

        if not name_entered:
            pygame.draw.rect(screen, color, input_box, 2, border_radius=8)
            text_surface = font_title.render(user_name, True, TEXT_DARK)
            screen.blit(text_surface, (input_box.x + 15, input_box.y + 5))
            if active and cursor_visible:
                cursor_rect = pygame.Rect(input_box.x + 18 + text_surface.get_width(), input_box.y + 10, 3, 30)
                pygame.draw.rect(screen, TEXT_DARK, cursor_rect)
        elif not profile_selected:
            # Show Adult/Kid buttons
            for btn, label in ((btn_adult, "Adult"), (btn_kid, "Kid")):
                clr = NIRYO_LIGHT_BLUE if btn.collidepoint(mp) else NIRYO_BLUE
                pygame.draw.rect(screen, BUTTON_SHADOW, btn.move(4, 4), border_radius=12)
                pygame.draw.rect(screen, clr, btn, border_radius=12)
                txt = font_main.render(label, True, (255, 255, 255))
                screen.blit(txt, txt.get_rect(center=btn.center))
        else:
            # Show difficulty and utility buttons
            button_configs = [
                (btn_easy, "Easy", BTN_EASY_COLOR, BTN_EASY_HOVER),
                (btn_med, "Medium", BTN_MEDIUM_COLOR, BTN_MEDIUM_HOVER),
                (btn_hard, "Hard", BTN_HARD_COLOR, BTN_HARD_HOVER)
            ]
            for btn, label, base_color, hover_color in button_configs:
                clr = hover_color if btn.collidepoint(mp) else base_color
                pygame.draw.rect(screen, BUTTON_SHADOW, btn.move(4, 4), border_radius=12)
                pygame.draw.rect(screen, clr, btn, border_radius=12)
                text_color = TEXT_DARK if label == "Medium" else (255, 255, 255)
                txt = font_main.render(label, True, text_color)
                screen.blit(txt, txt.get_rect(center=btn.center))
            """"
            utility_buttons = [
                (btn_place_cards, "Place Cards"),
                (btn_collect_cards, "Collect Cards")
            ]
            for btn, label in utility_buttons:
                clr = NIRYO_LIGHT_BLUE if btn.collidepoint(mp) else NIRYO_BLUE
                pygame.draw.rect(screen, BUTTON_SHADOW, btn.move(4,4), border_radius=12)
                pygame.draw.rect(screen, clr, btn, border_radius=12)
                txt = font_main.render(label, True, (255, 255, 255))
                screen.blit(txt, txt.get_rect(center=btn.center))
            """
        pygame.display.flip()
        clock.tick(FPS)
    difficulty = difficulty_selection

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
    global game_phase, winner_message, temporary_message
    global current_turn, score_human, score_robot, squares_to_flip_back
    global robot_status_message
    global ICON_CACHE, cell_image

    status, event = msg.get("status"), msg.get("event")
    if event == "CACHE_BUST":
        path = msg.get("image_path")
        if path in ICON_CACHE:
            del ICON_CACHE[path] # Remove the old surface from the cache
            print(f"[GUI] Cleared image cache for {path}.")

    if status == "reveal":
        sq, path = msg["square"], msg["image_path"]
        if cell_state.get(sq) != CellState.BACK:
            return
        if path not in ICON_CACHE:
            try:
                surf = pygame.image.load(path).convert_alpha()
                # Recreate the scaled image after a resize
                ICON_CACHE[path] = pygame.transform.smoothscale(surf, (CELL_W-24, CELL_H-24))
            except Exception as e:
                print(f"Error loading image {path}: {e}")
                pass
        cell_state[sq] = CellState.FACE_UP
        cell_image[sq] = ICON_CACHE.get(path)

    elif status == "matched":
        for sq in msg.get("squares", []):
            cell_state[sq] = CellState.MATCHED
        recent_clicks.clear()

    elif status in ("mismatch", "flip_back"):
        squares_to_flip_back = msg.get("squares",[])[:]
        pygame.time.set_timer(FLIP_BACK_EVENT, 2000, loops=1)

    elif status == "reset":
        global RESET_DESTINATION
        reset_gui_state()
        if RESET_DESTINATION == "intro":
            global game_phase
            game_phase = "intro"

    if event == "turn":
        current_turn = msg.get("player", "human")
        banner_text = "Your Turn" if current_turn == "human" else "Niryo's Turn"
        start_typewriter_animation("banner", banner_text)
    elif event == "score":
        score_human = msg.get("human_score", score_human)
        score_robot = msg.get("robot_score", score_robot)
        start_typewriter_animation("score_human", f"{player_name}: {score_human}")
        start_typewriter_animation("score_robot", f"Niryo: {score_robot}")
    elif event == "game_over":
        game_phase = "game_over"
        winner_name = player_name if msg['winner'] == 'human' else 'Niryo'
        if msg['winner'] == 'Tie':
             winner_message = f"It's a TIE! {msg['human_score']} points each."
        else:
             winner_message = f"{winner_name} WON! Final Score: {msg['human_score']}–{msg['robot_score']}"
    elif event == "GOTO_INTRO":
        game_phase = "intro"
    if event == "HINT_FLASH":
        squares = msg.get("squares", [])
        
        # 1. Flip the identified cards FACE_UP
        for sq in squares:
            # We must skip matched cards
            if cell_state.get(sq) != CellState.MATCHED:
                cell_state[sq] = CellState.FACE_UP
        
        # 2. Start the timer to flip them back after 5 seconds
        pygame.time.set_timer(HINT_FLASH_END, 5000, loops=1) # 5-second flash
    
    if event == "SCREEN_MESSAGE":
        temporary_message = msg.get("text", "")
        pygame.time.set_timer(MESSAGE_TIMER_EVENT, 3000, loops=1) # Display for 3 seconds
    if event == "SCREEN_MESSAGE_STATUS":
        robot_status_message = msg.get("text", "")
        # Reset the typewriter animation with the new text
        start_typewriter_animation("robot_status", robot_status_message)
        # Set the timer to clear it (Note: timer is set by the sender thread)
        # We rely on the receiver's loop to execute the timer event.


def run_gui() -> None:

    global recent_clicks, game_phase, difficulty, screen
    global RESET_DESTINATION
    pygame.time.set_timer(INTRO_SOUND_EVENT, 500, loops=1)
    show_intro()


    hover_lbl = None
    reset_gui_state()
    if difficulty:
        square_queue.put({"event": "set_difficulty", "difficulty": difficulty})
    running = True

    while running:
        if game_phase == "intro":
            show_intro()
            reset_gui_state()
            game_phase = "playing"
            if difficulty:
                square_queue.put({"event": "set_difficulty", "difficulty": difficulty})

        update_typewriter_animations()

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
            
            elif ev.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
                reset_gui_state()

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_q:
                    shutdown_program()
            
            if ev.type == HINT_FLASH_END:
                # Action: Flip the hint cards back over
                for sq in ALL_SQUARE_IDS:
                    # Check if the card is FACE_UP AND NOT permanently matched
                    if cell_state[sq] == CellState.FACE_UP and cell_state[sq] != CellState.MATCHED:
                        cell_state[sq] = CellState.BACK
            global temporary_message
            if ev.type == MESSAGE_TIMER_EVENT:
                temporary_message = ""
            if ev.type == ROBOT_STATUS_EVENT:
                global robot_status_message
                robot_status_message = ""
                start_typewriter_animation("robot_status", "")
                
            if game_phase == "playing":
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    # --- HANDLE HINT BUTTON CLICK (NEW) ---
                    if difficulty == "easy" and current_turn == "human":
                        if btn_hint.collidepoint(mouse_pos):
                            # Send command to the logic thread to find a pair
                            square_queue.put({"event": "GET_HINT"})
                            # Add visual/audio feedback for hint requested here if needed
                            
                            # Skip the rest of the mouse handling so it doesn't try to pick a card
                            continue

                    if btn_restart.collidepoint(mouse_pos):
                         
                        RESET_DESTINATION = "game"
                        square_queue.put({"event": "RESTART_GAME"})
                    elif btn_back.collidepoint(mouse_pos):
                        recent_clicks.clear()
                        RESET_DESTINATION = "intro"
                        square_queue.put({"event": "GOTO_INTRO"})
                        play_sound("intro")
                        show_intro()
                        reset_gui_state()
                        if difficulty:
                            square_queue.put({"event": "set_difficulty", "difficulty": difficulty})
                            
                        #running = False


                    elif current_turn == "human" and hover_lbl and len(recent_clicks) < 2:
                        if hover_lbl not in recent_clicks:
                            play_sound("picking")
                            square_queue.put(hover_lbl)
                            recent_clicks.append(hover_lbl)

                elif ev.type == FLIP_BACK_EVENT:
                    for sq in squares_to_flip_back:
                        cell_state[sq] = CellState.BACK
                    squares_to_flip_back.clear()
                    recent_clicks.clear()

            elif game_phase == "game_over":
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if btn_restart.collidepoint(mouse_pos):
                        RESET_DESTINATION = "game"
                        square_queue.put({"event": "RESTART_GAME"})
                        

        draw_board(hover_lbl, mouse_pos)
        if game_phase == "game_over":
            if not confetti_particles:  # Create confetti only once
                for _ in range(200):  # Create 200 confetti particles
                    x = random.randint(0, WINDOW_W)
                    y = random.randint(-WINDOW_H, 0)
                    x_vel = random.uniform(-2, 2)
                    y_vel = random.uniform(1, 5)
                    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                    confetti_particles.append(Confetti(x, y, x_vel, y_vel, color))

            # Update and draw confetti
            for particle in confetti_particles:
                particle.update()
                particle.draw(screen)

            if "winner_msg" not in animation_states or animation_states["winner_msg"]['full_text'] != winner_message:
                 start_typewriter_animation("winner_msg", winner_message)

            overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 200))
            screen.blit(overlay, (0,0))

            winner_text = animation_states.get("winner_msg", {}).get("visible_text", "")
            wm_surf = font_banner.render(winner_text, True, TEXT_DARK)
            wm_rect = wm_surf.get_rect(center=(WINDOW_W / 2, WINDOW_H / 2 - 50))
            screen.blit(wm_surf, wm_rect)

        pygame.display.flip()
        clock.tick(FPS)

    shutdown_program()

if __name__=="__main__":
    run_gui()