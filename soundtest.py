import os

# The name of the main folder containing your sound categories
SOUND_ROOT = "sounds"

def list_all_sound_files_recursively():
    """
    Scans the SOUND_ROOT directory and all its subdirectories, printing a
    structured list of all folders and the .wav files within them.
    """
    print(f"Recursively listing contents of the '{SOUND_ROOT}' directory...")
    print("-" * 50)

    # Check if the main sounds directory exists
    if not os.path.isdir(SOUND_ROOT):
        print(f"❌ Error: The directory '{SOUND_ROOT}' was not found.")
        print("Please make sure you are running this script in the same location as your 'sounds' folder.")
        return

    # os.walk() will traverse the directory tree top-down
    # dirpath is the path of the current directory
    # _ (we use an underscore) is for the list of subdirectories in dirpath
    # filenames is a list of the files in dirpath
    found_any_files = False
    for dirpath, _, filenames in sorted(os.walk(SOUND_ROOT)):
        # We only want to process folders that contain .wav files
        wav_files = sorted([f for f in filenames if f.endswith(".wav")])

        if wav_files:
            found_any_files = True
            # Get a clean, relative path to display as the category name
            category_name = os.path.relpath(dirpath, '.')
            print(f"\n📁 Category: {category_name}")

            for wav_file in wav_files:
                print(f"   🎵 {wav_file}")

    if not found_any_files:
        print("⚠️ No .wav files were found in any subdirectories.")

    print("-" * 50)


if __name__ == "__main__":
    list_all_sound_files_recursively()