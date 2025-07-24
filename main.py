import multiprocessing
import threading

from game_gui import run_gui
from memory_robot import main_loop


def start_robot():
    print("[LAUNCH] Starting robot thread...")
    main_loop()


def start_gui():
    print("[LAUNCH] Starting GUI thread...")
    run_gui()


def main():
    print("[RUN_ALL] Launching Niryo Memory Game System")

    # Start robot in background thread
    robot_thread = threading.Thread(target=start_robot, daemon=True)
    robot_thread.start()

    # Run GUI in main thread
    try:
        start_gui()
    except KeyboardInterrupt:
        print("[EXIT] Keyboard interrupt. Shutting down...")


if __name__ == "__main__":
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass  # Already set

    main()
