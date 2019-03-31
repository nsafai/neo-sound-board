"""Lasers: A tower defense game by Nicolime and Neptunius."""

import time
import random
# import adafruit_trellism4
import adafruit_trellis_express

COLORS = [0xFF0000, 0xFF5F00, 0xFFFF00, 0x00FF00, 0x00FFFF, 0x0000FF, 0xAA00FF]
RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, MAGENTA = COLORS
BLACK, WHITE, GRAY, DARK_GRAY = 0x000000, 0xFFFFFF, 0x444444, 0x222222
LEFT, RIGHT = GREEN, MAGENTA
LASER, SHIELD, WEAK_SHIELD = RED, BLUE, 0x000044  # Dark blue


def is_valid(coord):
    x, y = coord
    return 0 <= x < 8 and 0 <= y < 4

def index_of(coord):
    x, y = coord
    return y * 8 + x


class Game(object):

    def __init__(self):
        self.trellis = adafruit_trellis_express.TrellisM4Express(rotation=0)
        self.trellis.pixels._neopixel.brightness = 0.1  # 0.01 for chill play at night
        self.last_pressed_keys = set([])
        self.last_pressed_key = (0, 0)  # (8, 8)
        self.blank_color = BLACK
        self.rainbow_offset = 0
        self.rainbow_board()
        self.fill_board(int(DARK_GRAY//2))
        self.fill_board(BLACK)

    def rainbow_board(self):
        for _ in range(4):
            self.board = [COLORS[(i + self.rainbow_offset) % len(COLORS)] for i in range(8*4)]
            self.rainbow_offset -= 1
            self.color_board()

    def create_board(self):
        self.board = [self.blank_color for index in range(8*4)]
        for col in (0, 1, 6, 7):
            for row in range(4):
                coord = col, row
                self.board[index_of(coord)] = LASER if col in (0, 7) else SHIELD

        self.color_board()

    def keys_pressed(self):
        now_pressed = set(self.trellis.pressed_keys)
        new_presses = list(now_pressed - self.last_pressed_keys)
        self.last_pressed_keys = now_pressed
        return new_presses

    def fill_board(self, color=WHITE):
        self.trellis.pixels.fill(color)

    def draw_lasers_shields(self):
        # Draw lasers (far left and right columns)
        for col in 0, 7:
            for row in range(4):
                key = col, row
                color = self.board[index_of(key)]
                self.trellis.pixels[key] = color
        # Draw shields (second columns from edge)
        for col in 1, 6:
            for row in range(4):
                key = col, row
                color = self.board[index_of(key)]
                self.trellis.pixels[key] = color
                # self.board[index_of(coord)] = SHIELD

    def color_board(self):
        # colors = {}  # Only cells that need to be recolored
        for row in 0, 3, 2, 1:
            for col in range(8):
                key = col, row
                color = self.board[index_of(key)]
                # Collect only cells that need to be recolored
                # if color != self.blank_color:
                #     colors[key] = color
                # Color all cells with their board color (slow)
                self.trellis.pixels[key] = color
        # Blank out board (fast)
        # self.fill_board(self.blank_color)
        # Color select cells only
        # for key, color in sorted(colors.items()):
        #     self.trellis.pixels[key] = color

    def color_keys(self, keys, color=None):
        for key in keys:
            key_color = self.board[index_of(key)] if color is None else color
            self.trellis.pixels[key] = key_color

    def flash_keys(self, keys, color=None, times=3, delay=0.1):
        for _ in range(times-1):
            self.color_keys(keys, BLACK)
            time.sleep(delay)
            self.color_keys(keys, color)
            time.sleep(delay)
        self.color_keys(keys)
        time.sleep(delay)

    def play(self):
        keys_pressed = []
        lasers = []
        player = RIGHT

        # Loop until someone wins
        won = False
        while not won:
            # Redraw lasers and shields
            # self.draw_lasers_shields()

            # Handle laser movement and interactions
            for index, laser in enumerate(lasers):
                # Unpack laser: [(col, row), player]
                key, player = tuple(laser)
                col, row = key

                # Determine left or right player directions
                laser_dir = +1 if player is LEFT else -1
                opp_home_col = 7 if player is LEFT else 0
                opp_shield_col = 6 if player is LEFT else 1

                # Move laser in player's direction
                new_col = col + laser_dir
                new_key = new_col, row
                # TODO: Check if new coordinates are in bounds
                if not is_valid(new_key):
                    lasers[index] = None
                    continue

                near_object = self.board[index_of(new_key)]
                # Laser hit opponent's shield and shield is not yet destroyed
                if new_col == opp_shield_col and near_object in (SHIELD, WEAK_SHIELD):
                    # Weaken or destroy shield
                    new_object = WEAK_SHIELD if near_object == SHIELD else BLACK
                    self.board[index_of(new_key)] = new_object
                    self.color_keys([new_key], new_object)
                    lasers[index] = None  # Mark laser to be destroyed
                # Advance laser in its direction
                elif 0 <= new_col <= 7:
                    lasers[index][0] = new_key  # Update laser's coordinates
                    prior_color = self.board[index_of(key)]  # Cell's old color
                    self.color_keys([key], prior_color)  # Color prior cell
                    self.color_keys([new_key], player)  # Color laser's cell

            # Filter out all lasers that have been marked as dead
            lasers = list(filter(lambda b: b is not None, lasers))

            # Check for new input from users
            keys_pressed = self.keys_pressed()
            if keys_pressed:
                key = keys_pressed[0]
                col, row = key
                print('Key pressed:', key)
                # Left player's laser
                if col == 0:
                    player = LEFT
                # Right player's laser
                elif col == 7:
                    player = RIGHT
                # Not a laser
                else:
                    player = None
                # Create laser shot
                if player:
                    lasers.append([key, player])
                    self.color_keys([key], player)

                # TODO: Check if someone won by destroying opponent's lasers
                # won = find_winner()
                # TODO: Display winner by flashing board with winner's color
                # self.wipe(player, delay=0.05, direction='outward')
                # self.wipe(player, delay=0.1, direction='inward')
                # self.color_board()


def main():
    game = Game()
    while True:
        game.create_board()
        game.play()


if __name__ == '__main__':
    main()