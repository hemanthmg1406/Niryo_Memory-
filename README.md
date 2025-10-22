# Niryo Memory Match: An AI-Powered Robotic Memory Game

-----

### Project Description

This project is a sophisticated implementation of the classic memory card game, where a human player competes against a Niryo Ned robotic arm. The robot leverages a computer vision system to identify, remember, and match cards, showcasing an impressive integration of robotics, artificial intelligence, and human-computer interaction. The system features a rich graphical user interface (GUI) for the human player, complete with audio-visual feedback to create an engaging and interactive experience.

-----

### Features

  * **Human-Robot Interaction:** Engage in a two-player memory game against a Niryo Ned robotic arm, providing a unique and interactive experience.
  * **Advanced Computer Vision:** The robot utilizes its camera and the **SIFT (Scale-Invariant Feature Transform)** algorithm to scan the playing area, extract features from card images, and intelligently "remember" their locations and identities.
  * **Intelligent Game Logic:** The core game logic, managed by a dedicated module, handles turn-based gameplay, sophisticated match-checking using **PCA (Principal Component Analysis)** and **KNN (K-Nearest Neighbors)**, game state updates, and winner determination.
  * **Rich Graphical User Interface (GUI):** A user-friendly and responsive interface, built with Pygame, allows the human player to interact with the game. It provides real-time feedback on scores, turns, and game status, with a modern dashboard-style layout.
  * **Engaging Auditory Feedback:** The system includes a comprehensive library of sound effects for various game events, including human and robot turns, correct and incorrect matches, and game win/loss scenarios. Different audio profiles ("adult" and "kid") are available for a customized experience.
  * **Precise Robotic Control:** The project includes robust control over the Niryo Ned robot's movements. This includes calibration, homing, and precise actions for picking up, scanning, and placing cards using pre-recorded positions.
  * **Multi-threaded/Multi-processing Architecture:** The application runs the GUI and the robot control logic in separate threads/processes, ensuring a smooth and responsive user experience without interruptions from the robot's operations.

-----

### Hardware and Software Requirements

#### Hardware

  * **Niryo Ned/Ned2 Robot:** The project is specifically designed for the Niryo Ned or Ned2 robotic arm.
  * **Camera:** A camera compatible with the Niryo robot is required for the vision system.
  * **Speakers/Audio Output:** Necessary for the audio feedback features.

#### Software

  * **Python 3.x:** The project is developed in Python.
  * **pyniryo2:** The official Python library for controlling the Niryo robot.
  * **OpenCV:** The `opencv-python` library is used for computer vision tasks.
  * **Pygame:** Used for creating the GUI and handling audio playback.
  * **NumPy:** For numerical operations, especially in image processing and robot control.
  * **scikit-learn:** The `sklearn` library is used for PCA in the matching algorithm.

-----

### File Structure

The project is organized into the following directories and files:

  * `main.py`: The main entry point for the application. It initializes and manages the GUI and robot threads.
  * `game_gui.py`: Manages the entire graphical user interface, including layout, animations, and user input.
  * `memory_logic.py`: Contains the core logic for the memory game, handling turns, matching, scoring, and game state.
  * `memory_robot.py`: Manages the robot's actions, including vision-based card scanning, physical card movements, and communication with the game logic.
  * `sift_utils.py`: Provides helper functions for computer vision tasks using SIFT for feature extraction and matching.
  * `user_feedback.py`: A module for playing audio feedback for different game events.
  * `recorded_positions.py`: Stores pre-recorded positions for the robot's arm, crucial for precise movements.
  * `memory_queues.py`: Defines the queues used for inter-thread communication between the GUI and robot logic.
  * `config.py`: A configuration file for storing constants like the robot's IP address, vision parameters, and game settings.
  * `stackandunstack.py`: Contains functions for the robot to stack and unstack cards, used for board setup and cleanup.
  * `robot_interface.py`: A module to control the robot's LED ring for visual feedback.
  * `scanned_cards/`: A directory where the robot stores images of the cards it has scanned.
  * `sounds/`: A directory containing sub-folders with a rich library of sound effects for various game events.
  * `test.ipynb`: A Jupyter notebook for testing and debugging the vision system and robot movements.
  * `test_gui.py`: A simplified version of the GUI, likely used for initial development and testing.

-----

### How to Run

1.  **Install Dependencies:** Ensure all required Python libraries are installed. You can install them using `pip`:

    ```bash
    pip install pygame opencv-python pyniryo2 numpy scikit-learn
    ```

2.  **Hardware Setup:**

      * Set up your Niryo Ned robot and connect it to the same network as your computer.
      * Ensure the robot is in the correct operating pose and that the memory cards are placed on the designated game board within the robot's reach.

3.  **Configuration:**

      * Open the `config.py` file and verify that the `ROBOT_IP_ADDRESS` matches your robot's IP address.
      * You can also adjust other parameters in this file, such as vision thresholds and default difficulty.

4.  **Run the Main Script:** Execute the `main.py` file from your terminal:

    ```bash
    python main.py
    ```

-----

### Gameplay

1.  **Game Start:** The application will launch, and you'll be greeted with an intro screen. Enter your name and select an audio profile ("Adult" or "Kid").
2.  **Difficulty Selection:** After entering your name and choosing a profile, you'll be prompted to select a difficulty level ("Easy", "Medium", or "Hard").
3.  **Human's Turn:** The game starts with the human's turn. The GUI will prompt you to click on two cards to flip them.
4.  **Robot's Turn:** After your turn, the robot will take its turn, using its camera to scan the cards and its memory to make a match.
5.  **Matching:**
      * If a match is made (by either player), a point is awarded, and the cards are removed from the board. The player who made the match gets another turn.
      * If there is no match, the cards are flipped back over, and the turn passes to the other player.
6.  **Winning:** The game concludes when all cards have been matched. The player with the most matches is declared the winner. A "Game Over" screen with a confetti animation will be displayed. You can then choose to play again or exit.
