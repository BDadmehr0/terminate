import os
import sys
import termios
import signal
import time
import random
import json  # Import json module to save player data
from pynput import keyboard

# Character
PLAYER_CH = "P"  # character a player
ENEMY_CH = "E"  # character a enemy
EMPTY_CH = "_"  # character a map empty
BOX_CH = "B"  # character a box

# Global variables
player_position = 0  # Initial player position in the map
GAME_STATUS = False  # Start with game not running
old_settings = None  # Define old_settings globally
keys_pressed = set()  # Set to track currently pressed keys
enemies = []  # List to hold enemy positions
boxes = []  # List to hold box positions
score = 0  # Player's score
player_lives = 3  # Player starts with 3 lives
player_data_file = "data.json"  # File to save player data
show_attack_message = False  # To control when to show the attack message
attack_message_shown = False  # To make sure message is only shown once

# Allowed keys: only 'w', 'a', 's', 'd', and control keys like Ctrl+Z, Ctrl+C
ALLOWED_KEYS = {
    "w",
    "a",
    "s",
    "d",
    "e",  # Key for attacking
    keyboard.Key.ctrl_l,
    keyboard.Key.ctrl_r,
    keyboard.KeyCode.from_char("x"),
}


# Color definitions
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


class SystemCall:
    @staticmethod
    def hide_cursor():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    @staticmethod
    def show_cursor():
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    @staticmethod
    def clear_screen():
        sys.stdout.write("\033[H\033[J")
        sys.stdout.write(f"Player Lives: {player_lives}/3\n")  # Display player lives
        sys.stdout.flush()

    @staticmethod
    def get_terminal_size():
        return os.get_terminal_size()

    @staticmethod
    def handle_exit_signal(signum, frame):
        SystemCall.show_cursor()  # Ensure the cursor is shown
        os.system("clear")
        global old_settings  # Make sure we're using the global old_settings
        SystemCall.restore_echo(old_settings)
        print("exit")
        save_player_data()  # Save player data before exiting
        sys.exit(0)

    @staticmethod
    def disable_echo():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        new_settings = termios.tcgetattr(fd)
        new_settings[3] = new_settings[3] & ~termios.ECHO  # Disable echo
        termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
        return old_settings

    @staticmethod
    def restore_echo(old_settings):
        fd = sys.stdin.fileno()
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class SystemInputs:
    def __init__(self):
        self.keys_pressed = set()
        self.listener = keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release
        )
        self.listener.start()

    def on_press(self, key):
        try:
            if hasattr(key, "char") and key.char in ALLOWED_KEYS:
                self.keys_pressed.add(key.char)
            elif key in ALLOWED_KEYS:
                self.keys_pressed.add(key)
        except AttributeError:
            pass

    def on_release(self, key):
        try:
            if hasattr(key, "char") and key.char in ALLOWED_KEYS:
                self.keys_pressed.remove(key.char)
            elif key in ALLOWED_KEYS:
                self.keys_pressed.remove(key)
        except KeyError:
            pass

    def stop(self):
        self.listener.stop()


class Map:
    def __init__(self):
        self.columns, self.lines = (
            SystemCall.get_terminal_size()
        )  # Use the SystemCall method to get terminal size

        self.generate_enemies()  # Generate enemies when map is created
        self.generate_boxes()  # Generate boxes when map is created

    def generate_boxes(self):
        """Generate boxes with a 0.5% chance on the map."""
        global boxes
        boxes = []  # Reset boxes for a new game
        for i in range(self.columns):
            if random.random() < 0.005:  # 0.5% chance to spawn a box
                boxes.append(i)  # Add box at the position i

    def generate_enemies(self):
        """Generate enemies with a 20% chance in every 5% of the map."""
        global enemies
        enemies = []  # Reset enemies for a new game
        for i in range(self.columns):
            if random.random() < 0.05:  # 20% chance to spawn an enemy
                enemies.append(i)  # Add enemy at the position i

    def move_enemies_towards_player(self):
        """Move enemies one step towards the player."""
        global enemies, player_lives, GAME_STATUS
        new_enemies = []
        for enemy_pos in enemies:
            if enemy_pos < player_position:
                new_pos = enemy_pos + 1  # Move right towards player
            elif enemy_pos > player_position:
                new_pos = enemy_pos - 1  # Move left towards player
            else:
                # Enemy reached the player, decrease player's lives
                player_lives -= 1
                print(
                    f"{Colors.RED}Enemy hit you! Lives remaining: {player_lives}{Colors.RESET}"
                )
                if player_lives <= 0:
                    print(f"{Colors.RED}Game Over!{Colors.RESET}")
                    GAME_STATUS = False
                    return
                continue  # Do not add this enemy to new list, it's dead now

            new_enemies.append(new_pos)  # Update enemies' positions
        enemies = new_enemies
        time.sleep(0.1)  # Slows down enemy movement

    def draw(self):
        indexed_line = ""
        for i in range(self.columns):
            if i == player_position:
                indexed_line += PLAYER_CH
            elif i in enemies:
                indexed_line += f"{Colors.RED}{ENEMY_CH}{Colors.RESET}"
            elif i in boxes:
                indexed_line += f"{Colors.YELLOW}{BOX_CH}{Colors.RESET}"
            elif i == self.columns - 1:
                indexed_line += ">"
            else:
                indexed_line += EMPTY_CH

        sys.stdout.write(indexed_line + "\n")
        sys.stdout.flush()

        self.check_attack_option()
        # Check if the player has been moved to a new map
        self.check_new_map()

    def check_new_map(self):
        """If the player reaches the last character, move them to a new map.""""
        global player_position
        if player_position == self.columns - 1:
            print(f"{Colors.BLUE}You reached the end! Loading new map...{Colors.RESET}")
            time.sleep(2)
            player_position = 0  # Move player to the beginning of a new map
            self.generate_enemies()  # Creates new enemies
            self.generate_boxes()  # Creates new boxes

    def check_attack_option(self):
        """Check if player is next to an enemy or box and show corresponding messages."""
        global show_attack_message, attack_message_shown

        if (
            player_position in enemies
            or player_position - 1 in enemies
            or player_position + 1 in enemies
        ):
            if not attack_message_shown:  # Only show the message once
                print(f"{Colors.YELLOW}You can attack by pressing 'E'.{Colors.RESET}")
                attack_message_shown = True
                show_attack_message = True
                time.sleep(2)  # Pause for 2 seconds after showing the message
        elif player_position in boxes:
            print(f"{Colors.GREEN}You found a box! Press 'E' to open it.{Colors.RESET}")


def show_menu():
    """Display the welcome menu and handle user input."""
    global GAME_STATUS, old_settings
    while True:
        os.system("clear")  # Clear the screen
        print("Welcome to the Game!")
        print("1. Start Game")
        print("2. Help")
        print("3. Exit")

        # Enable echo for user input in the menu
        old_settings = SystemCall.restore_echo(old_settings)
        choice = input("Please choose an option (1, 2 or 3): ")

        # Restore echo to disabled after menu input
        old_settings = SystemCall.disable_echo()

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
        "Help - Page 2: The objective of the game is to navigate through the map.",
        "You can explore different areas and avoid obstacles.",
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
        "position": player_position,
        "score": score,
        "lives": player_lives,
        "enemies": enemies,  # Save enemies positions
    }
    with open(player_data_file, "w") as file:
        json.dump(player_data, file)


def load_player_data():
    """Load player position, score, lives, and enemies from a JSON file."""
    global player_position, score, player_lives, enemies
    if os.path.exists(player_data_file):
        with open(player_data_file, "r") as file:
            player_data = json.load(file)
            player_position = player_data.get(
                "position", 0
            )  # Default to 0 if not found
            score = player_data.get("score", 0)  # Default to 0 if not found
            player_lives = player_data.get(
                "lives", 3
            )  # Default to 3 lives if not found
            enemies = player_data.get(
                "enemies", []
            )  # Default to empty list if not found


# Register signal handlers
signal.signal(signal.SIGTSTP, SystemCall.handle_exit_signal)  # Handles Ctrl+Z (SIGTSTP)
signal.signal(signal.SIGINT, SystemCall.handle_exit_signal)  # Handles Ctrl+C (SIGINT)

# Disable input and save old settings
old_settings = SystemCall.disable_echo()

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
            if player_position in enemies:
                enemies.remove(player_position)  # Eliminate the enemy
                score += 100  # Increase points
            elif player_position - 1 in enemies:
                enemies.remove(player_position - 1)  # Eliminate the enemy on the left.
                score += 100
            elif player_position + 1 in enemies:
                enemies.remove(player_position + 1)  # Eliminate the enemy on the right.
                score += 100
            elif player_position in boxes:
                boxes.remove(player_position)  # Delete box after opening
                reward = random.choice(["Extra Life", "Score Boost", "Nothing"])
                reward = random.choice(["Extra Life", "Score Boost", "Speed Boost", "Penalty"])
                if reward == "Extra Life":
                    player_lives += 1
                    print(f"{Colors.GREEN}You received an extra life! Lives: {player_lives}{Colors.RESET}")
                elif reward == "Score Boost":
                    score += 50
                    print(f"{Colors.GREEN}You received a score boost! Score: {score}{Colors.RESET}")
                elif reward == "Speed Boost":
                    # Improved player movement speed for a short time
                    speed_boost = True
                elif reward == "Penalty":
                    player_lives -= 1
                    print(f"{Colors.RED}The box was cursed! You lost a life! Lives: {player_lives}{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}The box was empty!{Colors.RESET}")
                time.sleep(0.5)

        # Adjust player position based on key presses
        if "a" in input_handler.keys_pressed and player_position > 0:
            player_position -= 1
        elif (
            "d" in input_handler.keys_pressed
            and player_position < map_instance.columns - 1
        ):
            player_position += 1

        time.sleep(0.01)  # Slow down the game loop a bit
    except KeyboardInterrupt:
        SystemCall.handle_exit_signal(None, None)


input_handler.stop()  # Stop the listener
SystemCall.restore_echo(old_settings)
