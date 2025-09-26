
import os
import random
import time
import pyniryo2
from pyniryo2 import NiryoRobot, NiryoRos

# ──────────── INIT ────────────
robot_ip = "169.254.200.200"
robot = NiryoRobot(robot_ip)
ros_instance = NiryoRos(robot_ip)
sound_interface = pyniryo2.Sound(ros_instance)

# ──────────── SOUND CATEGORIES ────────────
sound_folder = "sounds"

categories = {
    "robot_win": "robot_win",
    "robot_turn": "robot_turn",
    "human_turn": "human_turn",
    "wrong_match_human": "wrong_match_human",
    "correct_match_human": "correct_match_human",
    "human_win": "human_win",
}

# ──────────── LOAD SOUND FILES ────────────
sound_files = []
for category, folder in categories.items():
    folder_path = os.path.join(sound_folder, folder)
    if os.path.isdir(folder_path):
        for file in os.listdir(folder_path):
            if file.endswith(".wav"):
                sound_name = file
                full_path = os.path.join(folder_path, file)
                sound_files.append((sound_name, full_path))

sound_dict = dict(sound_files)
sound_names = [name for name, _ in sound_files]

# ──────────── SAVE TO ROBOT (SKIP IF EXISTS) ────────────
def save_all_sounds():
    for name, path in sound_files:
        try:
            sound_interface.save(name, path)
            print(f"✅ Saved: {name}")
        except Exception as e:
            msg = str(e)
            if "already exists" in msg or "Failure to write" in msg:
                print(f"⚠️ Skipped (already exists): {name}")
            else:
                print(f"❌ Failed to save {name}: {msg}")

# ──────────── PLAY SOUND + LIGHTS ────────────
def play_sound(category):
    folder = categories.get(category)
    if not folder:
        print(f"❌ Unknown category: {category}")
        return

    folder_path = os.path.join(sound_folder, folder)
    options = [f for f in os.listdir(folder_path) if f.endswith(".wav")]
    if not options:
        print(f"⚠️ No sounds in category: {category}")
        return

    chosen = random.choice(options)
    try:
        robot.sound.play(chosen, wait_end=True)
        print(f"🔊 Played: {chosen}")

        # Optional LED effects
        if category == "wrong_match_human":
            robot.led_ring.flash([255, 0, 0], period=0.3, iterations=3, wait=True)
        elif category == "correct_match_human":
            robot.led_ring.solid([0, 255, 0])
            time.sleep(1)
            robot.led_ring.turn_off()
        elif category == "robot_win":
            robot.led_ring.breath([0, 0, 255], iterations=5, wait=True)
        elif category == "human_win":
            robot.led_ring.breath([255, 255, 0], iterations=5, wait=True)

    except Exception as e:
        print(f"❌ Error playing sound: {e}")

# ──────────── DEMO ────────────
if __name__ == "__main__":
    try:
        print("\n📦 Uploading all sounds to robot (skip if exists)...")
        save_all_sounds()

        print("\n🎮 Playing demo sound for each category...\n")
        for cat in categories:
            print(f"--- {cat} ---")
            play_sound(cat)
            time.sleep(0.5)

        print("\n✅ All done.")

    finally:
        robot.close