#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Developed by Dadmehr Emami at home - Github @BDadmehr0/emamidadmehr@gmail.com

"""
This module implements a terminal-based game.

It uses various libraries for functionality, including:
- JSON for saving and loading player data.
- OS and sys for system-level operations.
- Random for generating random events in the game.
- Signal and termios for handling terminal inputs.
- Time for delays and timers.
- pynput.keyboard for capturing keyboard input.
"""

import json  # Import json module to save player data
import os
import random
import signal
import sys
import termios
import time

from pynput import keyboard


# Character
PLAYER_CH = "P"  # character a player
ENEMY_CH = "E"  # character a enemy
EMPTY_CH = "_"  # character a map empty
BOX_CH = "B"  # character a box

# Global variables
ATTACK_MESSAGE_SHOWN = False  # To make sure message is only shown once
SHOW_ATTACK_MESSAGE = False  # To control when to show the attack message
PLAYER_DATA_FILE = "data.json"  # File to save player data
PLAYER_POSITION = 0  # Initial player position in the map
PLAYER_LIVES = 3  # Player starts with 3 lives
OLD_SETTINGS = None  # Define old_settings globally
keys_pressed = set()  # Set to track currently pressed keys
GAME_STATUS = False  # Start with game not running
enemies = []  # List to hold enemy positions
boxes = []  # List to hold box positions
SCORE = 0  # Player's score

# Allowed keys: only 'w', 'a', 's', 'd', and control keys like Ctrl+Z, Ctrl+C
ALLOWED_KEYS = {
    "a",  # Movement keys
    "d",
    "e",  # Key for attacking
    keyboard.Key.shift_l,  # Left shift
    keyboard.Key.shift_r,  # Right shift
}


class FGColors:
    """Foreground Colors"""

    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    @classmethod
    def all_colors(cls):
        """Returns a dictionary of all colors."""
        return {
            attr: value
            for attr, value in cls.__dict__.items()
            if not attr.startswith("__")
        }

    @classmethod
    def get_color(cls, color_name):
        """Returns the color code for a given foreground color name."""
        color_name = color_name.upper()
        return getattr(cls, color_name, cls.RESET)

    @classmethod
    def format_text(cls, text, color_name):
        """Returns the text formatted with the specified foreground color."""
        color_code = cls.get_color(color_name)
        return f"{color_code}{text}{cls.RESET}"


class BGColors:
    """Background Colors"""

    RESET = "\033[49m"
    RED = "\033[41m"
    GREEN = "\033[42m"
    YELLOW = "\033[43m"
    BLUE = "\033[44m"
    MAGENTA = "\033[45m"
    CYAN = "\033[46m"
    WHITE = "\033[47m"

    @classmethod
    def all_colors(cls):
        """Returns a dictionary of all colors."""
        return {
            attr: value
            for attr, value in cls.__dict__.items()
            if not attr.startswith("__")
        }

    @classmethod
    def get_color(cls, color_name):
        """Returns the color code for a given background color name."""
        color_name = color_name.upper()
        return getattr(cls, color_name, cls.RESET)

    @classmethod
    def format_text(cls, text, color_name):
        """Returns the text formatted with the specified background color."""
        color_code = cls.get_color(color_name)
        return f"{color_code}{text}{cls.RESET}"


class SystemCall:
    """
    A utility class for handling system-level operations in the terminal.

    This class provides static methods to:
    - Hide or show the terminal cursor.
    - Clear the terminal screen and display player-related information.
    - Retrieve the terminal's size.
    - Handle exit signals and restore terminal settings.
    - Disable and restore terminal input echoing for secure password input.

    Methods:
    hide_cursor()           - Hides the terminal cursor.
    show_cursor()           - Displays the terminal cursor.
    clear_screen()          - Clears the terminal screen and displays player data.
    get_terminal_size()     - Returns the current size of the terminal.
    handle_exit_signal()    - Handles the exit signal, restoring settings and saving data.
    disable_echo()          - Disables terminal input echo (used for secure input).
    restore_echo()          - Restores the terminal input echo settings.
    """

    @staticmethod
    def hide_cursor():
        """Hides the terminal cursor."""
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    @staticmethod
    def show_cursor():
        """Displays the terminal cursor."""
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    @staticmethod
    def clear_screen():
        """Clears the terminal screen and displays player data."""
        sys.stdout.write("\033[H\033[J")
        sys.stdout.write(
            f"Player Lives: {PLAYER_LIVES}/3\tScore: {SCORE}\n\n"
        )  # Display player lives
        sys.stdout.flush()

    @staticmethod
    def get_terminal_size():
        """Returns the current size of the terminal as a tuple (columns, lines)."""
        return os.get_terminal_size()

    @staticmethod
    def handle_exit_signal(_signum, _frame):
        """Handles the exit signal, restoring settings and saving player data."""
        SystemCall.show_cursor()  # Ensure the cursor is shown
        os.system("clear")
        SystemCall.restore_echo(OLD_SETTINGS)
        save_player_data()  # Save player data before exiting
        sys.exit(0)

    @staticmethod
    def disable_echo():
        """Disables terminal input echo for secure input (e.g., password)."""
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
            new_settings = termios.tcgetattr(fd)
            new_settings[3] = new_settings[3] & ~termios.ECHO
            termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
            return old_settings
        except Exception as e:
            print(f"Error in disable_echo: {e}")
            return None


    @staticmethod
    def restore_echo(OLD_SETTINGS):
        """Restores the terminal input echo settings."""
        if OLD_SETTINGS and isinstance(OLD_SETTINGS, list) and len(OLD_SETTINGS) == 7:
            fd = sys.stdin.fileno()
            termios.tcsetattr(fd, termios.TCSADRAIN, OLD_SETTINGS)
        else:
            print("Warning: OLD_SETTINGS is invalid, skipping restore.")



class SystemInputs:
    """
    A class to handle and track keyboard inputs in the system.

    This class listens for key presses and releases, keeping track of the keys that are pressed
    and whether the Shift key is held down. It also provides a method to stop the listener.

    Attributes:
    keys_pressed (set): A set of characters and/or keys currently pressed by the user.
    shift_pressed (bool): A flag indicating whether the Shift key is currently pressed.

    Methods:
    on_press(key)        - Callback method for when a key is pressed.
    on_release(key)      - Callback method for when a key is released.
    stop()               - Stops the keyboard listener.
    """

    def __init__(self):
        """
        Initializes the SystemInputs class, setting up the listener and key states.
        """
        self.keys_pressed = set()
        self.shift_pressed = False  # Track shift key state
        self.listener = keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release
        )
        self.listener.start()

    def on_press(self, key):
        """
        Callback method that is called when a key is pressed.

        Args:
        key (pynput.keyboard.Key): The key that was pressed.

        This method adds the key to the set of pressed keys, and checks if the Shift key
        was pressed.
        """
        try:
            if hasattr(key, "char"):
                if key.char in ALLOWED_KEYS:
                    self.keys_pressed.add(key.char)
            elif key in ALLOWED_KEYS:
                self.keys_pressed.add(key)

            # Check if shift is pressed
            if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                self.shift_pressed = True
        except AttributeError:
            pass

    def on_release(self, key):
        """
        Callback method that is called when a key is released.

        Args:
        key (pynput.keyboard.Key): The key that was released.

        This method removes the key from the set of pressed keys, and checks if the Shift key
        was released.
        """
        try:
            if hasattr(key, "char"):
                if key.char in ALLOWED_KEYS:
                    self.keys_pressed.remove(key.char)
            elif key in ALLOWED_KEYS:
                self.keys_pressed.remove(key)

            # Check if shift is released
            if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                self.shift_pressed = False
        except KeyError:
            pass

    def stop(self):
        """
        Stops the keyboard listener.

        This method stops the listener, halting key press and release tracking.
        """
        self.listener.stop()


class Map:
    """
    A class to represent the game map and handle map-related operations.

    This class generates and manages the game map, including the layout, enemies, and boxes.
    It also handles the movement of enemies towards the player, checking for attack options,
    and rendering the map on the screen.

    Attributes:
    columns (int): The number of columns in the map (based on terminal size).
    lines (int): The number of lines in the terminal (used for map generation).
    generated_map (str): A string representing the map layout with characters like '.', '_', 
                     '⌂', and '↟'.
    enemies (list): A list of positions where enemies are located on the map.
    boxes (list): A list of positions where boxes are located on the map.

    Methods:
    __init__(): Initializes the map, generates the layout, and creates enemies and boxes.
    generate_random_map(): Creates a random map with weighted probabilities for various characters.
    generate_boxes(): Generates boxes on the map with a 0.5% chance for each column.
    generate_enemies(): Spawns enemies on the map with a 20% chance, excluding the first 
                    and last 5 columns.
    move_enemies_towards_player(): Moves enemies toward the player and decreases lives on collision.
    draw(): Renders the map, showing the player, enemies, boxes, and other elements.
    check_new_map(): Checks if the player reached the map's end and moves to a new map.
    check_attack_option(): Checks if the player is adjacent to
                    an enemy or box and shows the attack message.
    """

    def __init__(self):
        """
        Initializes the map with the terminal size, generates the random layout,
        and creates enemies and boxes.
        """
        self.columns, self.lines = (
            SystemCall.get_terminal_size()
        )  # Use the SystemCall method to get terminal size

        self.generated_map = self.generate_random_map()  # Generate random character map
        self.generate_enemies()  # Generate enemies when map is created
        self.generate_boxes()  # Generate boxes when map is created

    def generate_random_map(self):
        """
        Generates a random map layout with weighted probabilities for different characters.

        Returns:
        str: A string representing the random map layout.
        """
        characters = [".", "_", "⌂", "↟"]
        weights = [40, 40, 1, 10]  # Heavier probability for '.' and '_'

        # Generate map by selecting characters based on weighted probabilities
        random_map = "".join(random.choices(characters, weights, k=self.columns))
        return random_map

    def generate_boxes(self):
        """
        Generates boxes on the map with a 0.5% chance for each column.

        This method places boxes at random positions on the map and updates the global `boxes` list.
        """
        global boxes
        boxes = []  # Reset boxes for a new game
        for i in range(self.columns):
            if random.random() < 0.005:  # 0.5% chance to spawn a box
                boxes.append(i)  # Add box at the position i

    def generate_enemies(self):
        """
        Generates enemies on the map with a 5% chance per column, excluding the first and last 5 columns.

        This method updates the global `enemies` list with the positions of the generated enemies.
        """
        global enemies
        enemies = []  # Reset enemies for the new map
        start_range = 50  # Starting from the 5th column
        end_range = self.columns - 5  # Ending at the 5th column from the end

        for i in range(start_range, end_range):
            if random.random() < 0.05:  # 5% chance for enemy generation
                enemies.append(i)  # Enemy is created at position i

    def move_enemies_towards_player(self):
        """
        Moves enemies towards the player, decreasing lives if an enemy reaches the player.

        This method updates the `enemies` list and checks if any enemy has collided with the player.
        """
        global enemies, PLAYER_LIVES, GAME_STATUS
        new_enemies = []
        for enemy_pos in enemies:
            if enemy_pos < PLAYER_POSITION:
                new_pos = enemy_pos + 1  # Move right towards the player
            elif enemy_pos > PLAYER_POSITION:
                new_pos = enemy_pos - 1  # Move left towards the player
            else:
                # Enemy reached the player, decrease player's lives
                PLAYER_LIVES -= 1
                print(
                    f"{FGColors.RED}Enemy hit you! Lives remaining: {PLAYER_LIVES}{FGColors.RESET}"
                )
                if PLAYER_LIVES <= 0:
                    print(f"{FGColors.RED}Game Over!{FGColors.RESET}")
                    GAME_STATUS = False
                    return
                continue  # Do not add this enemy to the new list, it's dead now

            new_enemies.append(new_pos)  # Update enemies' positions
        enemies = new_enemies
        time.sleep(0.1)  # Slows down enemy movement

    def draw(self):
        """
        Renders the game map on the terminal screen, displaying the player, enemies, boxes,
        and other map elements.

        This method updates the terminal display to show the current state of the map, including
        the player's position, enemies, boxes, and special characters.
        """
        indexed_line = ""
        for i in range(self.columns):
            if i == PLAYER_POSITION:
                indexed_line += f"{FGColors.BLUE}{PLAYER_CH}{FGColors.RESET}"
            elif i in enemies:
                indexed_line += f"{FGColors.RED}{ENEMY_CH}{FGColors.RESET}"
            elif i in boxes:
                indexed_line += f"{FGColors.YELLOW}{BOX_CH}{FGColors.RESET}"
            elif i == self.columns - 1:
                prefix = f"{BGColors.MAGENTA}{FGColors.WHITE}>{FGColors.RESET}{BGColors.RESET}"
                indexed_line += prefix
            else:
                # Here we specify that the character "↟" should be green.
                if self.generated_map[i] == "↟":
                    indexed_line += f"{FGColors.GREEN}↟{FGColors.RESET}"
                else:
                    indexed_line += self.generated_map[i]

        sys.stdout.write(indexed_line + "\n")
        sys.stdout.flush()

        self.check_attack_option()
        # Check if the player has been moved to a new map
        self.check_new_map()

    def check_new_map(self):
        """
        Checks if the player has reached the end of the map and moves them to a new map.

        If the player reaches the last column, this method resets the player's position and
        generates a new map with enemies and boxes.
        """
        global PLAYER_POSITION
        if PLAYER_POSITION == self.columns - 1:
            print(
                f"{FGColors.BLUE}You reached the end! Loading new map...{FGColors.RESET}"
            )
            time.sleep(2)
            PLAYER_POSITION = 0  # Move player to the beginning of a new map
            self.generate_enemies()  # Creates new enemies
            self.generate_boxes()  # Creates new boxes

    def check_attack_option(self):
        """
        Checks if the player is next to an enemy or box and displays the corresponding message.

        If the player is adjacent to an enemy or box, this method informs the player that they
        can attack or open the box.
        """
        global SHOW_ATTACK_MESSAGE, ATTACK_MESSAGE_SHOWN

        if (
            PLAYER_POSITION in enemies
            or PLAYER_POSITION - 1 in enemies
            or PLAYER_POSITION + 1 in enemies
        ):
            if not ATTACK_MESSAGE_SHOWN:  # Only show the message once
                print(
                    f"{FGColors.YELLOW}You can attack by pressing 'E'.{FGColors.RESET}"
                )
                ATTACK_MESSAGE_SHOWN = True
                SHOW_ATTACK_MESSAGE = True
        elif PLAYER_POSITION in boxes:
            print(
                f"{FGColors.GREEN}You found a box! Press 'E' to open it.{FGColors.RESET}"
            )


def show_menu():
    """Display the welcome menu and handle user input."""
    global GAME_STATUS, OLD_SETTINGS
    while True:
        os.system("clear")  # Clear the screen
        print("Welcome to the Game!")
        print("1. Start Game")
        print("2. Help")
        print("3. Exit")

        # Enable echo for user input in the menu
        OLD_SETTINGS = SystemCall.restore_echo(OLD_SETTINGS)
        choice = input("Please choose an option (1, 2 or 3): ")

        # Restore echo to disabled after menu input
        OLD_SETTINGS = SystemCall.disable_echo()
        if OLD_SETTINGS is None:
            print("Warning: Terminal settings could not be saved.")



        if choice == "1":
            load_player_data()  # Load player data before starting
            GAME_STATUS = True
            break
        elif choice == "2":
            show_help()
        elif choice == "3":
            SystemCall.handle_exit_signal(None, None)
        else:
            print("Invalid choice. Please choose 1, 2 or 3.")
            time.sleep(1)  # Pause before showing the menu again


def show_help():
    """Display help information and handle pagination."""
    help_texts = [
        "Help - Page 1: This is a simple game where you control a character.",
        "Use 'a' to move left and 'd' to move right.",
        "Press 'E' to attack enemies.",
        "Press Ctrl+C to exit the game at any time.",
        "",
        "Help - Page 2: To move faster, hold the 'Shift' key while pressing 'a' or 'd'.",
        "You can also attack enemies by pressing 'E' when you're next to them.",
        "Enemies appear randomly on the map, and you need to avoid or defeat them.",
        "",
        "Help - Page 3: You can find boxes scattered throughout the map.",
        "Press 'E' to open a box. It might contain:",
        "- An extra life",
        "- A score boost",
        "- A speed boost",
        "- Or a penalty (losing a life)",
        "Be careful, some boxes are cursed!",
        "",
        "Help - Page 4: Navigate the map, dodge enemies, and gather rewards.",
        "Try to survive as long as possible and rack up your score!",
        "Have fun playing!",
        "",
        "Press any key to return to the main menu.",
    ]

    for page in range(len(help_texts)):
        os.system("clear")  # Clear the screen
        print(help_texts[page])
        if page < len(help_texts) - 1:
            input("Press Enter to go to the next page...")
        else:
            input("Press Enter to return to the main menu...")


def save_player_data():
    """Save player position, score, lives, and enemies to a JSON file."""
    player_data = {
        "position": PLAYER_POSITION,
        "score": SCORE,
        "lives": PLAYER_LIVES,
        "enemies": enemies,  # Save enemies positions
    }
    with open(PLAYER_DATA_FILE, "w") as file:
        json.dump(player_data, file)


def load_player_data():
    """Load player position, score, lives, and enemies from a JSON file."""
    global PLAYER_POSITION, SCORE, PLAYER_LIVES, enemies, GAME_STATUS, OLD_SETTINGS
    while True:
        if os.path.exists(PLAYER_DATA_FILE):
            os.system("clear")
            print("1. Start new game")
            print("2. Load old game")
            print("3. Back")

            OLD_SETTINGS = SystemCall.restore_echo(OLD_SETTINGS)
            choice_menu2 = input("Please choose an option (1, 2 or 3): ")

            # Restore echo to disabled after menu input
            OLD_SETTINGS = SystemCall.disable_echo()
            if OLD_SETTINGS is None:
                print("Warning: Terminal settings could not be saved.")


            if choice_menu2 == "1":
                PLAYER_POSITION = 0
                SCORE = 0
                PLAYER_LIVES = 3
                enemies = []
                GAME_STATUS = True
                break
            elif choice_menu2 == "2":
                with open(PLAYER_DATA_FILE, "r") as file:
                    player_data = json.load(file)
                    PLAYER_POSITION = player_data.get(
                        "position", 0
                    )  # Default to 0 if not found
                    SCORE = player_data.get("score", 0)  # Default to 0 if not found
                    PLAYER_LIVES = player_data.get(
                        "lives", 3
                    )  # Default to 3 lives if not found
                    enemies = player_data.get(
                        "enemies", []
                    )  # Default to empty list if not found
                GAME_STATUS = True
                break
            elif choice_menu2 == "3":
                show_menu()
            else:
                print("Invalid choice. Please choose 1, 2 or 3.")
                time.sleep(1)  # Pause before showing the menu again
        else:
            PLAYER_POSITION = 0
            SCORE = 0
            PLAYER_LIVES = 3
            enemies = []
            GAME_STATUS = True
            break


# Register signal handlers
signal.signal(signal.SIGTSTP, SystemCall.handle_exit_signal)  # Handles Ctrl+Z (SIGTSTP)
signal.signal(signal.SIGINT, SystemCall.handle_exit_signal)  # Handles Ctrl+C (SIGINT)

# Disable input and save old settings
OLD_SETTINGS = SystemCall.disable_echo()
if OLD_SETTINGS is None:
    print("Warning: Terminal settings could not be saved.")


# Create an instance of SystemInputs
input_handler = SystemInputs()

map_instance = Map()  # Create a new map with enemies

# Show the welcome menu
show_menu()

while GAME_STATUS:
    SystemCall.hide_cursor()  # Hide the cursor
    try:
        SystemCall.clear_screen()  # Clears the screen and shows player lives

        map_instance.draw()  # Draw the game map

        # Move enemies towards player each frame
        map_instance.move_enemies_towards_player()

        # Check for attack or box opening
        if "e" in input_handler.keys_pressed:
            if PLAYER_POSITION in enemies:
                enemies.remove(PLAYER_POSITION)  # Eliminate the enemy
                SCORE += 100  # Increase points
            elif PLAYER_POSITION - 1 in enemies:
                enemies.remove(PLAYER_POSITION - 1)  # Eliminate the enemy on the left.
                SCORE += 100
            elif PLAYER_POSITION + 1 in enemies:
                enemies.remove(PLAYER_POSITION + 1)  # Eliminate the enemy on the right.
                SCORE += 100
            elif PLAYER_POSITION in boxes:
                boxes.remove(PLAYER_POSITION)  # Delete box after opening
                reward = random.choice(["Extra Life", "Score Boost", "Nothing"])
                reward = random.choice(
                    ["Extra Life", "Score Boost", "Speed Boost", "Penalty"]
                )
                if reward == "Extra Life":
                    PLAYER_LIVES += 1
                    print(
                        f"{FGColors.GREEN}Extra life! Lives: {PLAYER_LIVES}{FGColors.RESET}"
                    )
                elif reward == "Score Boost":
                    SCORE += 50
                    print(
                        f"{FGColors.GREEN}You received a score boost! "
                        f"Score: {SCORE}{FGColors.RESET}"
                    )

                elif reward == "Speed Boost":
                    # Improved player movement speed for a short time
                    speed_boost = True
                elif reward == "Penalty":
                    PLAYER_LIVES -= 1
                    print(
                        f"{FGColors.RED}The box was cursed! You lost a life! "
                        f"Lives: {PLAYER_LIVES}{FGColors.RESET}"
                    )

                else:
                    print(f"{FGColors.YELLOW}The box was empty!{FGColors.RESET}")
                time.sleep(0.5)

        # Adjust player position based on key presses
        if "a" in input_handler.keys_pressed and PLAYER_POSITION > 0:
            if input_handler.shift_pressed:  # If shift is pressed, move faster
                PLAYER_POSITION -= 2  # Move 2 steps left
            else:
                PLAYER_POSITION -= 1  # Normal speed
        elif (
            "d" in input_handler.keys_pressed
            and PLAYER_POSITION < map_instance.columns - 1
        ):
            if input_handler.shift_pressed:  # If shift is pressed, move faster
                PLAYER_POSITION += 2  # Move 2 steps right
            else:
                PLAYER_POSITION += 1  # Normal speed

        # time.sleep(0.01)  # Slow down the game loop a bit
    except KeyboardInterrupt:
        SystemCall.handle_exit_signal(None, None)


input_handler.stop()  # Stop the listener
SystemCall.restore_echo(OLD_SETTINGS)
