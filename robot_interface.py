from pyniryo2 import NiryoRobot
from config import ROBOT_IP_ADDRESS
import time

robot=NiryoRobot(ROBOT_IP_ADDRESS)

def set_robot_led(robot, state: str):
   
    # Define colors as RGB lists (R, G, B)
    COLOR_RED = [255, 0, 0]
    COLOR_GREEN = [0, 255, 0]
    COLOR_BLUE = [0, 0, 255]
    COLOR_PURPLE = [128, 0, 128] # Custom RGB for Purple
    
    # --- State: Robot is Planning/Waiting ---
    if state == "PLANNING":
        # While robot is planning its move - Breath Purple
        robot.led_ring.breath(COLOR_PURPLE, iterations=5, wait=False)

    elif state == "WAITING":
        # While robot is waiting for opponent (Human's Turn) - Breath Blue
        robot.led_ring.breath(COLOR_BLUE, iterations=0, wait=False) # Continuous breath

    # --- State: Match/Mismatch Outcomes ---
    elif state == "MATCH_ROBOT":
        # When robot makes a match - Chase Green
        # Assuming 'snake' can be adapted for a chase effect, similar to the original 'snake' example.
        robot.led_ring.snake(COLOR_GREEN, period=0.08, iterations=3, wait=True)
        robot.led_ring.turn_off()
        
    elif state == "MISMATCH_ROBOT":
        # When robot makes a mismatch - Solid Red (Flash is clearer for error)
        robot.led_ring.flash(COLOR_RED, period=0.3, iterations=3, wait=True) 
        robot.led_ring.turn_off()

    elif state == "MATCH_HUMAN":
        # When opponent makes a match - Snake Green
        robot.led_ring.snake(COLOR_GREEN, period=0.08, iterations=3, wait=True)
        robot.led_ring.turn_off()
        
    elif state == "MISMATCH_HUMAN":
        # When opponent makes a mismatch - Solid Red (Flash is clearer for error)
        robot.led_ring.flash(COLOR_RED, period=0.3, iterations=3, wait=True)
        robot.led_ring.turn_off()
        
    # --- Critical Failure States (Need clear, distinct signals) ---
    elif state == "SCAN_FAIL":
        # Scan failure - Fast Blinking Red/Magenta
        robot.led_ring.flash([255, 0, 255], period=0.15, iterations=5, wait=True) # Magenta flash
        robot.led_ring.turn_off()
        
    elif state == "HOME":
        # Default state (turn off or simple solid color)
        robot.led_ring.solid(COLOR_BLUE) # Simple solid blue