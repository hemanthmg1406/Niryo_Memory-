import sys, queue, pygame
from enum import Enum, auto
from typing import Dict, Tuple

from memory_queues import square_queue, gui_queue

# ──────────────────────── Layout & Colours ──────────────────────────────
WINDOW_W, WINDOW_H = 0, 0
ROWS, COLS       = 4, 5
GRID_X0, GRID_Y0 = 120, 120
BTN_W, BTN_H     = 180, 50
BTN_Y            = 780

GRAD_TOP    = (20, 24, 28)
GRAD_BOTTOM = (10, 12, 16)
CARD_BG     = (30, 36, 44)
HOVER_TINT  = (255, 255, 255, 50)
TEXT_MAIN   = (240, 240, 240)
TEXT_ACCENT = (160, 160, 160)
ACCENT      = (72, 212, 163)
MATCH_BORDER= (255, 195, 18)
BTN_NORMAL  = ACCENT
BTN_HOVER   = (98, 240, 190)
FPS         = 60

# ──────────────────────── Enums & Globals ───────────────────────────────
class CellState(Enum):
    BACK    = auto()
    FACE_UP = auto()
    MATCHED = auto()

cell_state:    Dict[str, CellState]
cell_image:    Dict[str, pygame.Surface]
ICON_CACHE:    Dict[str, pygame.Surface]
score_human    = 0
score_robot    = 0
current_turn   = "human"
recent_clicks: list[str]
selection_time = 0.0

# ──────────────────────── Initialization ────────────────────────────────
def init_globals() -> None:
    global cell_state, cell_image, ICON_CACHE
    global score_human, score_robot, current_turn
    global recent_clicks, selection_time
    global WINDOW_W, WINDOW_H
    global GRID_W, GRID_H, GRID_X, GRID_Y, CELL_W, CELL_H, BTN_Y

    WINDOW_W, WINDOW_H = screen.get_size()

    # compute max available
    avail_w = WINDOW_W - 2 * GRID_X0
    avail_h = WINDOW_H - 300

    # choose square cell (perfect squares)
    cell_side = min(avail_w // COLS, avail_h // ROWS)
    CELL_W = CELL_H = cell_side

    # center grid
    extra_x = (avail_w - COLS * cell_side) // 2
    extra_y = (avail_h - ROWS * cell_side) // 2
    GRID_X = GRID_X0 + extra_x
    GRID_Y = GRID_Y0 + extra_y

    # exact grid size
    GRID_W = COLS * cell_side
    GRID_H = ROWS * cell_side

    BTN_Y = WINDOW_H - 80

    cell_state    = {f"{chr(65+r)}{c+1}": CellState.BACK
                     for r in range(ROWS) for c in range(COLS)}
    cell_image    = {}
    ICON_CACHE    = {}
    score_human   = score_robot = 0
    current_turn  = "human"
    recent_clicks = []
    selection_time= 0.0

# ──────────────────────── Pygame Setup ─────────────────────────────────
pygame.init()
screen = pygame.display.set_mode((1280, 800))
init_globals()
pygame.display.set_caption("Niryo Memory Match – GUI")
clock = pygame.time.Clock()
font_small  = pygame.font.SysFont("Segoe UI", 24)
font_medium = pygame.font.SysFont("Segoe UI", 32)
font_banner = pygame.font.SysFont("Segoe UI Semibold", 64)

# card-back
temp = pygame.Surface((CELL_W-12, CELL_H-12), pygame.SRCALPHA)
pygame.draw.rect(temp, CARD_BG, temp.get_rect(), border_radius=16)
CARD_BACK = temp

# grid rects
grid_rects = {
    f"{chr(65+r)}{c+1}": pygame.Rect(
        GRID_X + c*CELL_W,
        GRID_Y + r*CELL_H,
        CELL_W, CELL_H
    )
    for r in range(ROWS) for c in range(COLS)
}
btn_restart = pygame.Rect(WINDOW_W//2 - BTN_W - 30, BTN_Y, BTN_W, BTN_H)
btn_quit    = pygame.Rect(WINDOW_W//2 + 30, BTN_Y, BTN_W, BTN_H)

# ──────────────────────── Utility Functions ─────────────────────────────
def draw_gradient(surface: pygame.Surface, top: Tuple[int,int,int], bottom: Tuple[int,int,int]) -> None:
    h = surface.get_height()
    for y in range(h):
        ratio = y / h
        r = int(top[0]*(1-ratio) + bottom[0]*ratio)
        g = int(top[1]*(1-ratio) + bottom[1]*ratio)
        b = int(top[2]*(1-ratio) + bottom[2]*ratio)
        pygame.draw.line(surface, (r,g,b), (0,y), (surface.get_width(),y))

def hit_test(pos) -> str|None:
    for lbl, rect in grid_rects.items():
        if rect.collidepoint(pos): return lbl
    return None

# ──────────────────────── Drawing ───────────────────────────────────────
def draw_board(hover_lbl: str|None, mouse_pos):
    draw_gradient(screen, GRAD_TOP, GRAD_BOTTOM)
    banner = "Your turn" if current_turn=="human" else "Robot's turn"
    bs = font_banner.render(banner, True, ACCENT)
    screen.blit(bs, (WINDOW_W//2-bs.get_width()//2, 20))

    # right messages
    msg_x, msg_y = GRID_X + GRID_W + 30, GRID_Y
    for i, lbl in enumerate(recent_clicks):
        surf = font_medium.render(f"Card {lbl} selected", True, TEXT_MAIN)
        screen.blit(surf, (msg_x, msg_y + i*(surf.get_height()+5)))

    # cards
    for lbl, rect in grid_rects.items():
        st = cell_state[lbl]
        inner = rect.inflate(-12, -12)
        pygame.draw.rect(screen, CARD_BG, inner)
        if st==CellState.BACK and lbl in recent_clicks:
            pygame.draw.rect(screen, ACCENT, inner, 4)
        if st==CellState.BACK and lbl==hover_lbl:
            ov = pygame.Surface((inner.width,inner.height), pygame.SRCALPHA)
            ov.fill(HOVER_TINT)
            screen.blit(ov, inner.topleft)
        if st!=CellState.BACK:
            img = cell_image.get(lbl)
            if img: screen.blit(img, img.get_rect(center=inner.center))
            if st==CellState.MATCHED:
                pygame.draw.rect(screen, MATCH_BORDER, inner, 4)

    # grid lines
    for r in range(ROWS+1):
        y = GRID_Y + r*CELL_H
        pygame.draw.line(screen, TEXT_ACCENT,
                         (GRID_X,        y),
                         (GRID_X+GRID_W, y), 1)
    for c in range(COLS+1):
        x = GRID_X + c*CELL_W
        pygame.draw.line(screen, TEXT_ACCENT,
                         (x, GRID_Y),
                         (x, GRID_Y+GRID_H), 1)

    # axis labels
    for r in range(ROWS):
        t = font_medium.render(chr(65+r), True, TEXT_ACCENT)
        screen.blit(t, (GRID_X-40, GRID_Y+r*CELL_H+CELL_H//2-t.get_height()//2))
    for c in range(COLS):
        t = font_medium.render(str(c+1), True, TEXT_ACCENT)
        screen.blit(t, (GRID_X+c*CELL_W+CELL_W//2-t.get_width()//2, GRID_Y-40))

    # scores
    sh = font_small.render(f"Human: {score_human}",True,TEXT_MAIN)
    sr = font_small.render(f"Robot: {score_robot}",True,TEXT_MAIN)
    screen.blit(sh,(40,WINDOW_H-120))
    screen.blit(sr,(WINDOW_W-40-sr.get_width(),WINDOW_H-120))

    # buttons
    for rect, label in ((btn_restart,"Restart Game"), (btn_quit,"Quit Game")):
        col = BTN_HOVER if rect.collidepoint(mouse_pos) else BTN_NORMAL
        pygame.draw.rect(screen, col, rect, border_radius=8)
        ts = font_small.render(label, True, (30,30,30))
        screen.blit(ts, (rect.centerx-ts.get_width()//2, rect.centery-ts.get_height()//2))

# ──────────────────────── Message Handling ──────────────────────────────
def handle_robot_msg(msg: dict) -> None:
    global score_human, score_robot, current_turn, recent_clicks

    # DEBUG: log every incoming message
    print(f"[GUI] Received from robot: {msg}")

    # Game events
    if 'event' in msg:
        ev = msg['event']
        if ev == 'score':
            if msg.get('player') == 'human':
                score_human += 1
            elif msg.get('player') == 'robot':
                score_robot += 1
        elif ev == 'turn':
            current_turn = msg['player']
        elif ev == 'reset':
            init_globals()
        elif ev == 'game_over':
            winner = msg.get('winner','Unknown').capitalize() + " wins!"
            win_surf = font_banner.render(winner, True, (255,80,80))
            screen.blit(win_surf, (WINDOW_W//2-win_surf.get_width()//2,
                                    WINDOW_H//2-win_surf.get_height()//2))
            pygame.display.flip(); pygame.time.wait(3000); pygame.quit(); sys.exit()
        return

    status = msg.get('status')

    # Reveal a single card
    if status == 'reveal':
        sq = msg.get('square')
        path = msg.get('image_path')
        if sq and path:
            if path not in ICON_CACHE:
                try:
                    surf = pygame.image.load(path).convert_alpha()
                except:
                    surf = pygame.Surface((CELL_W-6, CELL_H-6)); surf.fill((200,0,0))
                ICON_CACHE[path] = pygame.transform.smoothscale(surf, (CELL_W-6, CELL_H-6))
            cell_state[sq] = CellState.FACE_UP
            cell_image[sq] = ICON_CACHE[path]

    # Matched: handle list of squares
    elif status == 'matched':
        sqs = msg.get('squares') or [msg.get('square')]
        for sq in sqs:
            if sq in cell_state:
                cell_state[sq] = CellState.MATCHED

    # Flip-back: handle list of squares
    elif status == 'flip_back':
        sqs = msg.get('squares') or [msg.get('square')]
        for sq in sqs:
            if sq in cell_state:
                cell_state[sq] = CellState.BACK

    else:
        print(f"[GUI] Warning: Unhandled msg status '{status}'")
# ──────────────────────── Intro Screen ───────────────────────────────────
def show_intro() -> None:
    global difficulty
    btn_easy=pygame.Rect(WINDOW_W//2-300,WINDOW_H//2-25,200,50)
    btn_med =pygame.Rect(WINDOW_W//2-50 ,WINDOW_H//2-25,200,50)
    btn_hard=pygame.Rect(WINDOW_W//2+200,WINDOW_H//2-25,200,50)
    title_f=pygame.font.SysFont("Segoe UI Semibold",48)
    inst_f =pygame.font.SysFont("Segoe UI",28)
    title_s=title_f.render("Welcome to Memory Match",True,ACCENT)
    inst_s =inst_f.render("Select difficulty and start!",True,TEXT_MAIN)
    difficulty=None
    while difficulty is None:
        mp=pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit();sys.exit()
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                if btn_easy.collidepoint(mp): difficulty="easy"
                elif btn_med.collidepoint(mp): difficulty="medium"
                elif btn_hard.collidepoint(mp): difficulty="hard"
        draw_gradient(screen,GRAD_TOP,GRAD_BOTTOM)
        screen.blit(title_s,(WINDOW_W//2-title_s.get_width()//2,WINDOW_H//3-60))
        screen.blit(inst_s,(WINDOW_W//2-inst_s.get_width()//2,WINDOW_H//3))
        for btn,label in ((btn_easy,"Easy"),(btn_med,"Medium"),(btn_hard,"Hard")):
            clr=BTN_HOVER if btn.collidepoint(mp) else BTN_NORMAL
            pygame.draw.rect(screen,clr,btn,border_radius=8)
            txt=inst_f.render(label,True,(30,30,30))
            screen.blit(txt,(btn.centerx-txt.get_width()//2,btn.centery-txt.get_height()//2))
        pygame.display.flip(); clock.tick(FPS)

# ──────────────────────── Main Loop ─────────────────────────────────────
def run_gui() -> None:
    global recent_clicks, selection_time
    hover=None
    while True:
        now=pygame.time.get_ticks()/1000.0
        if len(recent_clicks)==2 and now-selection_time>=2.0:
            recent_clicks.clear()
        mp=pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit();sys.exit()
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                if btn_quit.collidepoint(mp): pygame.quit();sys.exit()
                elif btn_restart.collidepoint(mp):
                    init_globals()
                    while True:
                        try: square_queue.get_nowait()
                        except queue.Empty: break
                    while True:
                        try: gui_queue.get_nowait()
                        except queue.Empty: break
                    gui_queue.put({"event":"turn","player":"human"})
                elif current_turn=="human":
                    c=hit_test(mp)
                    if c and cell_state[c]==CellState.BACK and c not in recent_clicks:
                        square_queue.put(c)
                        recent_clicks.append(c)
                        selection_time=now
        nh=hit_test(mp)
        if nh!=hover:
            hover=nh
            cursor=pygame.SYSTEM_CURSOR_HAND if hover and cell_state[hover]==CellState.BACK else pygame.SYSTEM_CURSOR_ARROW
            pygame.mouse.set_cursor(cursor)
        try:
            while True: handle_robot_msg(gui_queue.get_nowait())
        except queue.Empty: pass
        draw_board(hover,mp)
        pygame.display.flip(); clock.tick(FPS)

if __name__=="__main__":
    show_intro()
    run_gui()
