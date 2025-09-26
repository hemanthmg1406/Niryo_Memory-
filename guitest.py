import pygame
import sys
import time

# --- Initialization ---
pygame.init()

# --- Constants ---
# Screen dimensions
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 600

# Colors (R, G, B)
BLACK = (0, 0, 0)
GREEN = (40, 255, 40) # A classic terminal green

# Framerate
FPS = 60

# --- Text and Animation Settings ---
TEXT_TO_TYPE = "Hello, world. This is a typewriter effect in Pygame..."
FONT_SIZE = 36

# Time in milliseconds between each character appearing
TYPING_SPEED = 50 

# Time in milliseconds for the cursor to complete one on/off cycle
CURSOR_BLINK_RATE = 500 

# --- Setup Display and Clock ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Typewriter Effect")
clock = pygame.time.Clock()

# --- Font Setup ---
# Using a monospaced font makes the cursor movement look more uniform.
# 'consolas' on Windows, 'menlo' on Mac, 'dejavusansmono' on Linux are good choices.
try:
    font = pygame.font.Font('consolas.ttf', FONT_SIZE)
except FileNotFoundError:
    print("Font not found, falling back to default monospaced font.")
    font = pygame.font.SysFont('monospace', FONT_SIZE)

# --- State Variables for the Animation ---
# The portion of the text that is currently visible
displayed_text = ''
# The index of the next character to be revealed
char_index = 0

# Timers for controlling animation speed
# pygame.time.get_ticks() returns the number of milliseconds since pygame.init() was called.
last_char_time = 0
last_blink_time = 0
cursor_visible = True
typing_complete = False

# --- Main Game Loop ---
running = True
while running:
    current_time = pygame.time.get_ticks()

    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # --- Update Logic ---
    
    # 1. Handle Typing Animation
    # Check if there are still characters to type out
    if not typing_complete:
        # Check if enough time has passed since the last character was typed
        if current_time - last_char_time > TYPING_SPEED:
            char_index += 1
            displayed_text = TEXT_TO_TYPE[:char_index]
            last_char_time = current_time
            
            # Check if we've typed the whole string
            if char_index >= len(TEXT_TO_TYPE):
                typing_complete = True

    # 2. Handle Cursor Blinking
    # Check if enough time has passed to toggle the cursor's visibility
    if current_time - last_blink_time > CURSOR_BLINK_RATE:
        cursor_visible = not cursor_visible
        last_blink_time = current_time
        
    # --- Drawing ---
    # 1. Clear the screen with a background color
    screen.fill(BLACK)
    
    # 2. Render the text that has been "typed" so far
    text_surface = font.render(displayed_text, True, GREEN)
    # Position the text. We'll use a fixed starting point.
    text_rect = text_surface.get_rect(topleft=(50, 50))
    screen.blit(text_surface, text_rect)

    # 3. Draw the cursor
    if cursor_visible:
        # Calculate the position for the cursor
        # It should appear right after the last character.
        cursor_x = text_rect.right + 2 # Add a small gap
        
        # If no text has been typed yet, the rect's width will be 0.
        # So we place the cursor at the starting x position.
        if char_index == 0:
            cursor_x = text_rect.left

        cursor_height = font.get_height()
        cursor_rect = pygame.Rect(cursor_x, text_rect.top, 3, cursor_height)
        pygame.draw.rect(screen, GREEN, cursor_rect)

    # 4. Update the display
    pygame.display.flip()
    
    # 5. Control the frame rate
    clock.tick(FPS)

# --- Quit ---
pygame.quit()
sys.exit()