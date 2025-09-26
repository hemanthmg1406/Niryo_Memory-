
import os
import random
import time
from pyniryo import NiryoRobot

# Connect to Niryo robot
robot = NiryoRobot("169.254.200.200")

# Path to your main sound folder
SOUND_ROOT = "sounds"

# Main function to play one random sound from a folder + LED effect
def play_sound(category):
    folder_path = os.path.join(SOUND_ROOT, category)
    if not os.path.isdir(folder_path):
        print(f"[SFX] Invalid category: {category}")
        return

    # Get all .wav files in the given folder
    wav_files = [f for f in os.listdir(folder_path) if f.endswith(".wav")]
    if not wav_files:
        print(f"[SFX] No sounds found in: {category}")
        return

    # Choose and play a random sound
    chosen = random.choice(wav_files)
    try:
        robot.sound.play(chosen, wait_end=True)
        print(f"[SFX] Played: {category}/{chosen}")
    except Exception as e:
        print(f"[SFX] Error playing sound: {e}")
        return

    # LED effects per category
    try:
        if category == "robot_win":
            robot.led_ring.breath([0, 0, 255], iterations=5, wait=True)  # Blue breath
        elif category == "robot_turn":
            robot.led_ring.snake([0, 255, 255], period=0.08, iterations=3, wait=True)  # Aqua snake
        elif category == "human_turn":
            robot.led_ring.go_up_and_down([255, 255, 0], iterations=2, wait=True)  # Yellow wave
        elif category == "wrong_match_human":
            robot.led_ring.flash([255, 0, 0], period=0.3, iterations=3, wait=True)  # Red flash
        elif category == "correct_match_human":
            robot.led_ring.solid([0, 255, 0])
            time.sleep(1)
            robot.led_ring.turn_off()
        elif category == "human_win":
            robot.led_ring.rainbow_cycle(iterations=3, wait=True)  # Rainbow finish
        else:
            robot.led_ring.rainbow(iterations=1, wait=True)  # fallback effect

    except Exception as e:
        print(f"[SFX] LED error: {e}")

