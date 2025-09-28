import os
import random
import time
# This is the corrected import statement
from pyniryo2 import NiryoRobot

# Connect to Niryo robot using the pyniryo2 library
robot = NiryoRobot("169.254.200.200")

# Path to your main sound folder
SOUND_ROOT = "sounds"

# Main function to play one random sound from a folder + LED effect
def play_sound(category):
    """
    Plays a random .wav file from the specified category folder.
    The category can now be a path like 'level/easy' or a filename like 'intro'.
    """
    # os.path.join handles creating the correct path (e.g., "sounds/level/easy")
    folder_path = os.path.join(SOUND_ROOT, category)

    # First, check if the provided path is a directory
    if os.path.isdir(folder_path):
        # Get all .wav files in the given folder
        wav_files = [f for f in os.listdir(folder_path) if f.endswith(".wav")]
        if not wav_files:
            print(f"[SFX] No sounds found in: {category}")
            return

        # Choose and play a random sound from the list
        chosen_file = random.choice(wav_files)
        try:
            # Now that 'robot' is from pyniryo2, this .sound attribute will exist
            robot.sound.play(chosen_file, wait_end=True)
            print(f"[SFX] Played: {category}/{chosen_file}")
        except Exception as e:
            print(f"[SFX] Error playing sound from category '{category}': {e}")
            return

    # If not a directory, check if it's a direct file reference (e.g., "intro")
    else:
        filepath = f"{folder_path}.wav"
        if os.path.isfile(filepath):
            sound_name = os.path.basename(filepath)
            try:
                robot.sound.play(sound_name, wait_end=True)
                print(f"[SFX] Played: {sound_name}")
            except Exception as e:
                print(f"[SFX] Error playing sound file '{sound_name}': {e}")
        else:
            print(f"[SFX] Invalid category or file path: {category}")
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