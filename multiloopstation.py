# standard library
import array
import math
import os
import random
import time

# custom libraries
from lib import adafruit_trellis_express

# hidden libraries on hardware
import adafruit_adxl34x
import audioio
import board
import busio

# custom modules
from wave_parsing import parse_wav


# GLOBAL VARIABLES
INSTR_ROWS = [0, 1] # we'll use bottom 2 rows for insruments
NUM_INSTR_ROWS = len(INSTR_ROWS) # useful for matrixes with >8x4 buttons
LOOPER_ROWS = [2, 3] # we'll use top 2 rows for insruments
NUM_SEQ_ROWS = len(LOOPER_ROWS)
NUM_COLUMNS = 8
TICKER_COLOR = 0xFFA500 
INSTR_FAMILY_COLORS = {
    "bass": 0x16a085, # teal
    "cow": 0xe67e22, # orange
    "effect": 0x8e44ad, # purple
    "glitch": 0x2ecc71, # green
    "hihat": 0xf1c40f, # yellow
    "kick": 0x2980b9, # blue
    "snare": 0xc0392b, # red
    "tom": 0x34495e, # dark blue
}
DIFF_BTWN_COLORS = 0x23

# GLOBAL FUNCTIONS
def get_instr_index(row, col):
    # returns index of instrument pressed
    return col * NUM_INSTR_ROWS - INSTR_ROWS[0] + row

def get_loop_index(row, col):
    # returns index of button pushed on loops rows
    if row == LOOPER_ROWS[-1]: # if top row
        return col
    else: # if bottom row
        return col + 8 # bottom row starts at loop index 8


# BOARD CLASS
class Board:
    def __init__(self, type=adafruit_trellis_express.TrellisM4Express(rotation=90)):
        self.type = type # Our keypad + neopixel driver
        # Init keypad with preset settings
        self.pixels = self.type.pixels
        self.setBrightness(0.05)
        self.clearPixels()
        # Setup instruments
        self.instr_idx = 0 # default to first instrument
        self.instrument_urls = self.find_wav_files("/sounds")
        self.num_sounds = len(self.instrument_urls)
        # Setup Sound
        self.parse_wav_files() # Parse 1st file to figure out what format its in
        self.mixer = audioio.Mixer(voice_count=self.num_sounds, sample_rate=self.wave_format['sample_rate'],
                                    channel_count=self.wave_format['channels'],
                                    bits_per_sample=16, samples_signed=True)
        self.audio.play(self.mixer)
        # Setup Colors
        self.instrument_colors = []
        self.assign_colors() # assign a unique color for every instrument
        self.color_buttons() # light up the buttons with instrument colors
        # Setup Beat
        self.tempo = 180  # Starting BPM
        self.loop_length = 16
        self.current_step = 15 # we actually start on the last step since we increment first
        self.current_press = set() # currently pressed buttons
        self.loops = [] # will keep track of all instrument loops
        # Assign colors and sounds to keys
        self.samples = self.load_instruments()
        # Play a sample when finished with initial load
        random_sample = random.choice(self.samples)
        self.mixer.play(random_sample) # play random sample
        self.pressed_keys = [] # keeps track of buttons pressed (updated regularly)
        # Run the loop
        self.playing = True

    ################## PIXELS ####################
    def setBrightness(self, percentFloat):
        # set brightness to number between 0.0-1.0
        self.pixels._neopixel.brightness = percentFloat
    
    def clearPixels(self):
        # Clear all pixels
        self.pixels._neopixel.fill(0)
        self.pixels._neopixel.show()

    ################## SOUNDS ####################
    def find_wav_files(self, folderUrl):
        instrument_urls = [] # starts blank
        # Sounds must all (1) have the same sample rate and (2) be mono or stereo (no mix-n-match!)
        # go through every file in /sounds directory
        for file in sorted(os.listdir(folderUrl)):
            # get all .wav files but ignore files that start with "."
            if file.endswith(".wav") and not file.startswith("."):
                # append those to SOUNDS
                instrument_urls.append(folderUrl + "/" + str(file))
        return instrument_urls
    
    def parse_wav_files(self):
        self.wave_format = parse_wav(self.instrument_urls[0])
        if self.wave_format['channels'] == 1:
            self.audio = audioio.AudioOut(board.A1)
        elif self.wave_format['channels'] == 2:
            self.audio = audioio.AudioOut(board.A1, right_channel=board.A0)
        else:
            raise RuntimeError("All sound files must be either mono or stereo!")

    # assign unique instrument colors AND load instruments into memory
    def load_instruments(self):
        samples = []
        # for every instrument in list of instrument urls:
        for cur_idx in range(len(self.instrument_urls)):
            # -- load into memory --
            wave_file = open(self.instrument_urls[cur_idx], "rb") # open the corresponding wave file
            sample = audioio.WaveFile(wave_file) # convert wave file
            samples.append(sample) # append to list of sound samples
            self.loops.append([0] * self.loop_length) # starting state of loops for all instruments
        return samples

    # set button to color at instr_index in instrument_colors array
    def assign_colors(self):
        for instrument_url in self.instrument_urls:
            # get instrument_family from prefix of file name (e.g. __ in sounds/__XX.wav)
            instr_fam = instrument_url[8:-6]
            print(instr_fam)
            # get instrument_number from filename w/o extension (e.g. XX in sounds/__XX.wav)
            instr_num = instrument_url[-6:-4]
            print(instr_num)
            # lookup instrument family color in a dictionary (ie bass is blue, cymbal is yellow)
            instr_fam_color = INSTR_FAMILY_COLORS[instr_fam]
            # use instrument number to get unique color within range of family color
            instr_color = instr_fam_color + int(instr_num) * DIFF_BTWN_COLORS
            # save these colors to the list of colors
            self.instrument_colors.append(instr_color) # append drum color
    
    def color_buttons(self, starting_instr=0):
        max_instr_at_once = NUM_INSTR_ROWS * NUM_COLUMNS
        for instr_idx in range(starting_instr, max_instr_at_once):
            # get row and column
            row = (instr_idx - starting_instr) % 2
            col = (instr_idx - starting_instr) // 2
            self.pixels[(row, col)] = self.instrument_colors[instr_idx] # assign color on trellis

    ################## TICKER ####################
    def redraw_after_ticker(self):
        # redraw the last step to remove the ticker (e.g. show what was there before ticker)
        # row is 3 (top row) for for first 8 counts, then 2 (second row) for counts 9-16
        row = 3 if self.current_step < 8 else 2
        # current_step ranges from 0-15 but col can only be equal to 0-7, so we subtract 8
        col = self.current_step % NUM_COLUMNS
        color = 0 # color is black by default
        if self.loops[self.instr_idx][self.current_step]: # if pixel colored before ticker
            color = self.instrument_colors[self.instr_idx] # restore that color after ticket moves
        self.pixels[(row, col)] = color
    
    def move_ticker(self):
        # draw the ticker for every count, where loop_size = 16 counts
        # row is 3 for for first 8 counts, then 2 for 9-16
        row = 3 if self.current_step < 8 else 2
        # current_step ranges from 0-15 but col can only be equal to 0-7, so we subtract 8
        col = self.current_step % NUM_COLUMNS
        color = TICKER_COLOR # default ticker color
        # PLAY ALL INSTRUMENT SOUNDS
        # if instrument is supposed to play at current_step:
        for instr in range(len(self.loops)): # for every instrument index in loops
            if self.loops[instr][self.current_step]: # if instrument enabled at that step
                color = self.instrument_colors[instr] // 2 # show a slightly different ticker color
                self.mixer.play(self.samples[instr], voice=instr) # play the instrument's sound
        self.pixels[(row, col)] = color # light up the pixel
    
    ##################### PLAY LOOP ########################
    def loop(self):
        print("loop")
        while self.playing:
            stamp = time.monotonic() # stamp represents time at beginning of loop
            self.redraw_after_ticker() # redraw pixels as they appeared before ticker
            self.current_step = (self.current_step + 1) % 16 # next beat!
            self.move_ticker() # move yellow ticker

            # handle button presses while we're waiting for the next tempo beat
            while (time.monotonic() - stamp) < (60 / self.tempo):
                # grab currently pressed buttons from self.type (=board type)
                pressed = set(self.type.pressed_keys)
                # for every button pressed in last beat:
                for btn in pressed - self.current_press:
                    # print("Pressed down", btn)
                    row, col = btn[0], btn[1] # unwrap coordinates of pressed button
                    if row in INSTR_ROWS:
                        self.instr_idx = get_instr_index(row, col) # get instrument from button coordinates
                        self.mixer.play(self.samples[self.instr_idx], voice=self.instr_idx) # play sound of button pressed
                        # light up button at all indexes where instrument appears
                        for step, status in enumerate(self.loops[self.instr_idx]):
                            # print('step',step,'status',status)
                            # top row (row 3) for first 8 counts, second row after
                            row = 3 if step < 8 else 2
                            # step ranges from 0-15 but col can only be equal to 0-7, so we subtract 8
                            col = step % NUM_COLUMNS
                            color = 0 # default color
                            if status: # if instrument enabled at that count/step
                                color = self.instrument_colors[self.instr_idx] # set color to instrument color
                            self.pixels[(row, col)] = color
                    elif row in LOOPER_ROWS:
                        loop_idx = get_loop_index(row, col) # get loop index from button coordinates
                        # toggle instrument at loop_idx
                        # e.g. if it was previously enabled -> disable & vice-versa
                        self.loops[self.instr_idx][loop_idx] ^= True
                        if self.loops[self.instr_idx][loop_idx]: # if sound was just enabled
                            color = self.instrument_colors[self.instr_idx] # grab instrument's color
                        else: # if sound was just disabled
                            color = 0 # set color to 0 to turn off the pixel
                        self.pixels[(row, col)] = color # change color on the board
                self.current_press = pressed # update current_press

def main():
    board = Board()  # setup everything to be ready
    board.loop()


if __name__ == "__main__":
    # pass  # to avoid calling broken code above
    main()  # enable after refactor
