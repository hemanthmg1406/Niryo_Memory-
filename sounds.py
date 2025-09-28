import os
import random
import time
import pyniryo2
from pyniryo2 import NiryoRobot, NiryoRos

# ──────────── INIT ────────────
# Ensure the robot's IP address is correct
ROBOT_IP_ADDRESS = "169.254.200.200"
SOUND_ROOT = "sounds"

robot = None  # Initialize robot to None
print("Connecting to robot...")
try:
    robot = NiryoRobot(ROBOT_IP_ADDRESS)
    ros_instance = NiryoRos(ROBOT_IP_ADDRESS)
    sound_interface = pyniryo2.Sound(ros_instance)
    print("✅ Connection successful.")
except Exception as e:
    print(f"❌ Failed to connect to robot: {e}")
    exit()


# ──────────── UPLOAD ALL SOUNDS TO ROBOT ────────────
def upload_all_sounds():
    """
    Dynamically finds all .wav files in all subdirectories of SOUND_ROOT
    and uploads them to the robot.
    """
    print("\n📦 Starting sound upload process...")
    if not os.path.isdir(SOUND_ROOT):
        print(f"❌ Error: The root sound folder '{SOUND_ROOT}' was not found.")
        return

    # os.walk will go through the root folder and all its subdirectories
    for dirpath, _, filenames in os.walk(SOUND_ROOT):
        for filename in filenames:
            if filename.endswith(".wav"):
                sound_name = filename
                full_path = os.path.join(dirpath, filename)

                try:
                    sound_interface.save(sound_name, full_path)
                    print(f"✅ Uploaded: {sound_name}")
                except Exception as e:
                    msg = str(e)
                    if "already exists" in msg or "Failure to write" in msg:
                        print(f"⚠️  Skipped (already exists): {sound_name}")
                    else:
                        print(f"❌ ERROR uploading {sound_name}: {msg}")
    print("\n✅ Sound upload process complete.")


# ──────────── DEMO TO TEST A SOUND ────────────
def play_random_sound_from_category(category):
    """
    A helper function to test if sounds are working.
    """
    folder_path = os.path.join(SOUND_ROOT, category)
    if not os.path.isdir(folder_path):
        print(f"❌ Invalid category for demo: {category}")
        return

    wav_files = [f for f in os.listdir(folder_path) if f.endswith(".wav")]
    if not wav_files:
        print(f"⚠️ No sounds found in: {category}")
        return

    chosen = random.choice(wav_files)
    try:
        print(f"\n🔊 Playing test sound: {chosen} from category '{category}'")
        robot.sound.play(chosen, wait_end=True)
    except Exception as e:
        print(f"❌ Error playing sound: {e}")


# ──────────── MAIN EXECUTION ────────────
if __name__ == "__main__":
    try:
        upload_all_sounds()
        
        # Example of testing a sound
        # time.sleep(1)
        # play_random_sound_from_category("robot_win")

    finally:
        # The pyniryo2 library handles disconnection automatically when the script ends.
        # No explicit close() call is needed.
        print("\n👋 Script finished.")