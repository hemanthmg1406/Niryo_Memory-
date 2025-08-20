**Niryo Memory Match: An AI-Powered Robotic Memory Game**

***

### Project Description
This project implements a classic memory card game where a human player competes against a Niryo Ned robot. The robot uses a vision system to identify and remember the location of cards, demonstrating capabilities in computer vision and artificial intelligence. The system includes a graphical user interface (GUI) for the human player and provides auditory feedback for different game events.

***

### Features
* **Human-Robot Interaction:** Play a two-player memory game against a Niryo Ned robotic arm.
* **Computer Vision:** The robot uses its camera and **SIFT (Scale-Invariant Feature Transform)** to scan the playing area, identify card images, and "remember" their locations.
* **Game Logic:** The core game logic manages turns, checks for matches, updates the game state, and determines the winner.
* **Graphical User Interface (GUI):** A user-friendly interface allows the human player to select cards and provides real-time feedback on the game's progress.
* **Auditory Feedback:** The system includes sound files to provide engaging audio cues for human and robot turns, correct and incorrect matches, and victory/defeat.
* **Robotic Control:** The code controls the Niryo Ned robot's movements, including homing, picking up, and placing cards.

***

### Dependencies and Requirements
#### Hardware
* **Niryo Ned Robot:** The project is specifically designed to work with the Niryo Ned robotic arm.
* **Webcam/Camera:** A camera is required for the robot's vision system to capture images of the cards.
* **Speakers/Audio Output:** For the sound feedback feature.

#### Software
* **Python 3.x:** The project is written in Python.
* **Niryo Python API:** The `niryo_robot` library is essential for communicating with and controlling the robot.
* **OpenCV:** The `cv2` library is used for the computer vision tasks, including image processing and keypoint matching.
* **Pygame:** Used for the GUI and for playing sound effects.
* **Other Python Libraries:** `numpy` for numerical operations, `threading` for managing parallel tasks (GUI and robot control), `os` for file system operations, and `random` for shuffling cards.

***

### File Structure
The project is organized into the following directories and files:

* `main.py`: The main entry point for the application. It initializes the GUI, game logic, and robot threads.
* `game_gui.py`: Manages the graphical user interface using Pygame.
* `memory_logic.py`: Contains the core logic for the memory game, handling turns and matches.
* `memory_robot.py`: Manages the robot's actions, including vision, card movements, and memory.
* `sift_utils.py`: Provides helper functions for computer vision tasks using SIFT (Scale-Invariant Feature Transform) for image matching.
* `user_feedback.py`: Handles playing the audio feedback for different game events.
* `card_place.py`: Defines the coordinates and positions of the cards on the playing board.
* `recorded_positions.py`: Stores the pre-recorded positions for the robot's base movements.
* `memory_queues.py`: Used for inter-thread communication to synchronize robot actions and game state.
* `scanned_cards/`: A directory to store images of the cards captured by the robot's vision system.
* `sounds/`: A directory containing sub-folders with sound effects for game events.
* `test.ipynb`: A Jupyter notebook that likely contains testing and debugging code for the vision system.
* `memory.PNG`: Project image showcasing the game.
* `debug_preview.jpg` and `debug_masked.jpg`: Debugging images saved by the vision system.

***

### How to Run
1.  **Install Dependencies:** Ensure all required Python libraries are installed using `pip`.
    ```bash
    pip install pygame opencv-python niryo_robot numpy
    ```
2.  **Hardware Setup:** Set up your Niryo Ned robot and ensure it is connected to the same network as your computer. The robot must be in the correct operating pose, and the cards should be placed on the designated game board.
3.  **Run the Main Script:** Execute the `main.py` file from your terminal.
    ```bash
    python main.py
    ```

***

### Gameplay
1.  **Game Start:** The game will automatically start with the robot's turn.
2.  **Robot's Turn:** The robot will use its camera to "scan" the cards and will attempt to make a match based on its memory.
3.  **Human's Turn:** After the robot's turn, the GUI will prompt you to click on two cards to flip them.
4.  **Matches:** If you find a match, you will earn a point, and the robot will remove the cards from the board. If not, the cards will be flipped back over.
5.  **Winning:** The game ends when all cards have been matched. The player with the most matches wins.
