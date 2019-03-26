# standard library
import array
import math
import os
import random
import time

# custom libraries
import adafruit_trellis_express
import adafruit_adxl34x
import audioio
import board
import busio

# custom modules
from wave_parsing import parse_wav

################### GLOBALS ####################
INSTR_ROWS = [0, 1] # we'll use bottom 2 rows for insruments
NUM_INSTR_ROWS = len(INSTR_ROWS) # useful for matrixes with >8x4 buttons
LOOPER_ROWS = [2, 3] # we'll use top 2 rows for insruments
NUM_SEQ_ROWS = len(LOOPER_ROWS)
NUM_COLUMNS = 8

################# GLOBAL FUNCTIONS ##################
def get_instr_index(row, col):
    # returns index of instrument pressed
    return col * NUM_INSTR_ROWS - INSTR_ROWS[0] + row

def get_loop_index(row, col):
    # returns index of button pushed on loops rows
    if row == LOOPER_ROWS[-1]: # if top row
        return col
    else: # if bottom row
        return col + 8 # bottom row starts at loop index 8

################### BOARD CLASS ####################
class Board:

    def __init__(self, type = adafruit_trellis_express.TrellisM4Express(rotation=90)):
        self.type = type # Our keypad + neopixel driver
        # INIT KEYPAD with preset settings
        self.pixels = self.type.pixels
        self.setBrightness(0.05)
        self.clearPixels()
        # SOUNDS SETUP
        self.num_sounds = 0
        self.sounds = []
        self.find_wav_files("/sounds")
        self.instr_idx = 0 # default to first instrument
        # Parse the first file to figure out what format its in
        self.wave_format = parse_wav(self.sounds[0])
        if self.wave_format['channels'] == 1:
            self.audio = audioio.AudioOut(board.A1)
        elif self.wave_format['channels'] == 2:
            self.audio = audioio.AudioOut(board.A1, right_channel=board.A0)
        else:
            raise RuntimeError("All sound files must be either mono or stereo!")
        self.mixer = audioio.Mixer(voice_count=self.num_sounds, sample_rate=self.wave_format['sample_rate'],
                                channel_count=self.wave_format['channels'],
                                bits_per_sample=16, samples_signed=True)
        self.audio.play(self.mixer)
        # COLORS SETUP
        self.drum_colors = []
        self.ticker_color = 0xFFA500 # the color for the sweeping ticker
        # BEAT SETUP
        self.tempo = 180  # Starting BPM
        self.loop_length = 16
        self.playing = True
        self.current_step = 15 # we actually start on the last step since we increment first
        self.current_press = set() # currently pressed buttons
        self.loops = [] # will keep track of all instrument loops
        # ASSIGN COLORS/SOUNDS TO KEYS
        self.samples = self.assign_samples()
        # play a sample when finished with initial load
        random_sample = random.choice(self.samples)
        self.mixer.play(random_sample) # play random sample

    def setBrightness(self, percentFloat):
        # set brightness to number between 0.0-1.0
        self.pixels._neopixel.brightness = percentFloat
    
    def clearPixels(self):
        # Clear all pixels
        self.pixels._neopixel.fill(0)
        self.pixels._neopixel.show()

    def find_wav_files(self, folderUrl):
        # Sounds must all (1) have the same sample rate and (2) be mono or stereo (no mix-n-match!)
        # go through every file in /sounds directory
        for file in sorted(os.listdir(folderUrl)):
            # get all .wav files but ignore files that start with "."
            if file.endswith(".wav") and not file.startswith("."):
                # append those to SOUNDS
                self.sounds.append(folderUrl + str(file))
        print(self.sounds)
        self.num_sounds = len(self.sounds)
    
    def assign_samples():
        # allocating 16 buttons for sounds
        for col in range(NUM_COLUMNS): # across 8 columns
            for row in range(NUM_INSTR_ROWS): # across 2 rows
                cur_idx = NUM_INSTR_ROWS * col + row
                if cur_idx < len(SOUNDS): # never try to load sounds that don't exist
                    # TODO: Only keep parts that need to happen once on load
                    # rest goes inside a assign_colors // change_page function
                    # Generate a random color
                    instr_fam = SOUNDS[cur_idx][8:-6] # extract __ in sounds/__XX.wav
                    instr_num = SOUNDS[cur_idx][-6:-4] # extract XX in sounds/__XX.wav
                    instr_fam_num = abs(hash(instr_fam)) # hash instr fam
                    # TODO: USE DICTIONARY TO MAP INSTR FAM TO COLOR
                    instr_color = 0x000000 + instr_fam_num * 400000 + int(instr_num) * 2500
                    DRUM_COLORS.append(instr_color) # append drum color
                    trellis.pixels[(row, col)] = DRUM_COLORS[cur_idx] # assign color on trellis
                    wave_file = open(SOUNDS[cur_idx], "rb") # open the corresponding wave file
                    sample = audioio.WaveFile(wave_file) # convert wave file
                    samples.append(sample) # append to list of sound samples
                    loops.append([0] * loop_length) # starting state of loops for all instruments
                    # cur_idx += 1 # iterate cur_idx
        return samples


################## TICKER FUNCTIONS ####################
def redraw_after_ticker():
    # redraw the last step to remove the ticker (e.g. show what was there before ticker)
    # row is 3 (top row) for for first 8 counts, then 2 (second row) for counts 9-16
    row = 3 if current_step < 8 else 2
    # current_step ranges from 0-15 but col can only be equal to 0-7, so we subtract 8
    col = current_step % NUM_COLUMNS
    color = 0 # color is black by default
    if loops[instr_idx][current_step]: # if pixel colored before ticker
        color = DRUM_COLORS[instr_idx] # restore that color after ticket moves
    trellis.pixels[(row, col)] = color

def move_ticker():
    # draw the ticker for every count, where loop_size = 16 counts
    # row is 3 for for first 8 counts, then 2 for 9-16
    row = 3 if current_step < 8 else 2
    # current_step ranges from 0-15 but col can only be equal to 0-7, so we subtract 8
    col = current_step % NUM_COLUMNS
    color = TICKER_COLOR # default ticker color
    # PLAY ALL INSTRUMENT SOUNDS
    # if instrument is supposed to play at current_step:
    for instr in range(len(loops)): # for every instrument index in loops
        if loops[instr][current_step]: # if instrument enabled at that step
            color = DRUM_COLORS[instr] // 2 # show a slightly different ticker color
            mixer.play(samples[instr], voice=instr) # play the instrument's sound
    trellis.pixels[(row, col)] = color # light up the pixel


##################### PLAY LOOP ########################
while playing:
    stamp = time.monotonic() # stamp represents time at beginning of loop
    redraw_after_ticker() # redraw pixels as they appeared before ticker
    current_step = (current_step + 1) % 16 # next beat!
    move_ticker() # move yellow ticker
    # handle button presses while we're waiting for the next tempo beat
    while time.monotonic() - stamp < 60/tempo:
        # grab currently pressed buttons
        pressed = set(trellis.pressed_keys)
        # for every button pressed in last beat:
        for btn in pressed - current_press:
            # print("Pressed down", btn)
            row, col = btn[0], btn[1] # unwrap coordinates of pressed button
            if row in INSTR_ROWS:
                instr_idx = get_instr_index(row, col) # get instrument from button coordinates
                mixer.play(samples[instr_idx], voice=instr_idx) # play sound of button pressed
                # light up button at all indexes where instrument appears
                for step, status in enumerate(loops[instr_idx]):
                    # print('step',step,'status',status)
                    # top row (row 3) for first 8 counts, second row after
                    row = 3 if step < 8 else 2
                    # step ranges from 0-15 but col can only be equal to 0-7, so we subtract 8
                    col = step % NUM_COLUMNS
                    color = 0 # default color
                    if status: # if instrument enabled at that count/step
                        color = DRUM_COLORS[instr_idx] # set color to instrument color
                    trellis.pixels[(row, col)] = color
            elif row in LOOPER_ROWS:
                loop_idx = get_loop_index(row, col) # get loop index from button coordinates
                # toggle instrument at loop_idx
                # e.g. if it was previously enabled -> disable & vice-versa
                loops[instr_idx][loop_idx] ^= True
                if loops[instr_idx][loop_idx]: # if sound was just enabled
                    color = DRUM_COLORS[instr_idx] # grab instrument's color
                else: # if sound was just disabled
                    color = 0 # set color to 0 to turn off the pixel
                trellis.pixels[(row, col)] = color # change color on the board
        current_press = pressed # update current_press


def main():
    board = Board()  # setup everything to be ready
    board.loop()


if __name__ == "__main__":
    pass  # to avoid calling broken code above
    # main()  # enable after refactor