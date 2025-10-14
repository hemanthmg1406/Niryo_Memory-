from pyniryo2 import NiryoRobot
from config import ROBOT_IP_ADDRESS
import time

robot=NiryoRobot(ROBOT_IP_ADDRESS)

def set_robot_led(robot, state: str):
    
    # Define colors as RGB lists (R, G, B)
    COLOR_RED = [255, 0, 0]
    COLOR_GREEN = [0, 255, 0]
    COLOR_BLUE = [255, 0, 255]
    COLOR_PURPLE = [128, 0, 128] 
    COLOR_MAGENTA = [0, 0, 255] # For SCAN_FAIL
    
    # --- State: Robot is Planning/Waiting ---
    if state == "PLANNING":
        # Required: Alternate Purple. Using fast pulse/flash as the closest active state.
        robot.led_ring.flash(COLOR_PURPLE, period=0.35, iterations=0, wait=False) 

    elif state == "WAITING":
        # Required: Breath Blue.
        robot.led_ring.breath(COLOR_BLUE, iterations=0, wait=False) 

    # --- State: Match/Mismatch Outcomes ---
    elif state == "MATCH_ROBOT":
        # Required: Chase Green. Using faster snake pattern (0.05s) for a chase effect.
        robot.led_ring.snake(COLOR_GREEN, period=0.25, iterations=5, wait=True)
        robot.led_ring.turn_off()
        
    elif state == "MISMATCH_ROBOT":
        # Required: Solid Red.
        robot.led_ring.solid(COLOR_RED)
        time.sleep(2.0)
        robot.led_ring.turn_off()

    elif state == "MATCH_HUMAN":
        # Required: Snake Green.
        robot.led_ring.snake(COLOR_GREEN, period=0.3, iterations= 4, wait=True)
        robot.led_ring.turn_off()
        
    elif state == "MISMATCH_HUMAN":
        # Required: Solid Red.
        robot.led_ring.solid(COLOR_RED)
        time.sleep(2.0)
        robot.led_ring.turn_off()
        
    # --- Critical Failure States ---
    elif state == "SCAN_FAIL":
        # Fast Blinking Magenta
        robot.led_ring.flash(COLOR_MAGENTA, period=0.35, iterations=5, wait=True) 
        robot.led_ring.turn_off()
        
    elif state == "HOME":
        # Default state
        robot.led_ring.solid(COLOR_BLUE)