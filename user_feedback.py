import os
import random
import pygame

# Path to your main sound folder
SOUND_ROOT = "sounds"

# Cache for loaded sounds to improve performance
SOUND_CACHE = {}

def play_sound(category):
    """
    Plays a random .wav file from the specified category folder using pygame.
    The category can now be a path like 'level/easy' or a filename like 'intro'.
    """
    sound_path = None
    folder_path = os.path.join(SOUND_ROOT, category)

    if os.path.isdir(folder_path):
        wav_files = [f for f in os.listdir(folder_path) if f.endswith(".wav")]
        if not wav_files:
            print(f"[SFX] No sounds found in: {category}")
            return
        chosen_file = random.choice(wav_files)
        sound_path = os.path.join(folder_path, chosen_file)

    else:
        filepath = f"{folder_path}.wav"
        if os.path.isfile(filepath):
            sound_path = filepath

    if sound_path:
        if sound_path in SOUND_CACHE:
            SOUND_CACHE[sound_path].play()
        else:
            try:
                sound = pygame.mixer.Sound(sound_path)
                SOUND_CACHE[sound_path] = sound
                sound.play()
                print(f"[SFX] Played: {sound_path}")
            except pygame.error as e:
                print(f"[SFX] Error playing sound '{sound_path}': {e}")
    else:
        print(f"[SFX] Invalid category or file path: {category}")