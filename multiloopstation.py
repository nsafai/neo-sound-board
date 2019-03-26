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


################### KEYPAD SETUP ####################
# Init keypad with preset settings
trellis = adafruit_trellis_express.TrellisM4Express(rotation=90) # Our keypad + neopixel driver
trellis.pixels._neopixel.brightness = 0.05
# Clear all pixels
trellis.pixels._neopixel.fill(0)
trellis.pixels._neopixel.show()
INSTR_ROWS = [0, 1] # we'll use bottom 2 rows for insruments
NUM_INSTR_ROWS = len(INSTR_ROWS) # useful for matrixes with >8x4 buttons
SEQUENCER_ROWS = [2, 3] # we'll use top 2 rows for insruments
NUM_SEQ_ROWS = len(SEQUENCER_ROWS)
instr_idx = 0 # default to first instrument

def get_instr_index(row, col):
    # returns index of instrument pressed
    return col * NUM_INSTR_ROWS - INSTR_ROWS[0] + row

def get_loop_index(row, col):
    # returns index of button pushed on sequencer rows
    if row == SEQUENCER_ROWS[-1]: # if top row
        return col
    else: # if bottom row
        return col + 8 # bottom row starts at loop index 8


#################### IMPORT SOUNDS ####################
# Sounds must all (1) have the same sample rate and (2) be mono or stereo (no mix-n-match!)
SOUNDS = []
# go through every file in /sounds directory
for file in os.listdir("/sounds"):
    # get all .wav files but ignore files that start with "."
    if file.endswith(".wav") and not file.startswith("."):
        # append those to SOUNDS
        SOUNDS.append("/sounds/" + str(file))
print(SOUNDS)
num_sounds = len(SOUNDS)

# Parse the first file to figure out what format its in
wave_format = parse_wav(SOUNDS[0])

# Audio playback object - we'll go with either mono or stereo depending on
# what we see in the first file
if wave_format['channels'] == 1:
    audio = audioio.AudioOut(board.A1)
elif wave_format['channels'] == 2:
    audio = audioio.AudioOut(board.A1, right_channel=board.A0)
else:
    raise RuntimeError("All sound files must be either mono or stereo!")
mixer = audioio.Mixer(voice_count=num_sounds, sample_rate=wave_format['sample_rate'],
                        channel_count=wave_format['channels'],
                        bits_per_sample=16, samples_signed=True)
audio.play(mixer)


#################### COLOR SETUP ####################
DRUM_COLOR = []
# the color for the sweeping ticker
TICKER_COLOR = (255, 165, 0)


################### SEQUENCER SETUP ####################
tempo = 180  # Starting BPM
playing = True
current_step = 15 # we actually start on the last step since we increment first
current_press = set() # currently pressed buttons
sequencer = [] # will keep track of all instrument loops


############# ASSIGN COLORS/SOUNDS TO KEYS ###############
samples = []
cur_idx = 0

# allocating 16 buttons for sounds
for col in range(8): # across 8 columns
    for row in range(2): # across 2 rows
        # generate a random color
        instr_fam = SOUNDS[cur_idx][8:-6] # extract __ in sounds/"__"XX.wav
        instr_num = SOUNDS[cur_idx][-6:-4] # extract XX in sounds/"__"XX.wav
        instr_fam_num = abs(hash(instr_fam)) # hash instr fam
        instr_color = 0x000000 + instr_fam_num * 400000 + int(instr_num) * 2500
        DRUM_COLOR.append(instr_color) # append drum color
        trellis.pixels[(row, col)] = DRUM_COLOR[cur_idx] # assign color on trellis
        wave_file = open(SOUNDS[cur_idx], "rb") # open the corresponding wave file
        sample = audioio.WaveFile(wave_file) # convert wave file
        samples.append(sample) # append to list of sound samples
        sequencer.append([0] * 16) # starting state of sequencer for all instruments
        cur_idx += 1 # iterate cur_idx

# play a sample when finished with initial load
random_sample = random.choice(samples)
mixer.play(random_sample) # play random sample


################## TICKER FUNCTIONS ####################
def redraw_after_ticker():
    # redraw the last step to remove the ticker (e.g. show what was there before ticker)
    # row is 3 (top row) for for first 8 counts, then 2 (second row) for counts 9-16
    row = 3 if current_step < 8 else 2
    # current_step ranges from 0-15 but col can only be equal to 0-7, so we subtract 8
    col = current_step if current_step < 8 else (current_step - 8)
    color = 0 # color is black by default
    if sequencer[instr_idx][current_step]: # if pixel colored before ticker
        color = DRUM_COLOR[instr_idx] # restore that color after ticket moves
    trellis.pixels[(row, col)] = color

def move_ticker():
    # draw the ticker for every count, where loop_size = 16 counts
    # row is 3 for for first 8 counts, then 2 for 9-16
    row = 3 if current_step < 8 else 2
    # current_step ranges from 0-15 but col can only be equal to 0-7, so we subtract 8
    col = current_step if current_step < 8 else (current_step - 8)
    color = TICKER_COLOR # default ticker color
    # if instrument is supposed to play at current_step:
    for i in range(len(sequencer)): # for every instrument index in sequencer
        if sequencer[i][current_step]: # if instrument enabled at that step
            color = DRUM_COLOR[i] // 2 # show a slightly different ticker color
            mixer.play(samples[i], voice=i) # play the instrument's sound
    trellis.pixels[(row, col)] = color # light up the pixel


##################### PLAY LOOP ########################
while playing == True:
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
                for step, status in enumerate(sequencer[instr_idx]):
                    # print('step',step,'status',status)
                    # top row (row 3) for first 8 counts, second row after
                    row = 3 if step < 8 else 2
                    # step ranges from 0-15 but col can only be equal to 0-7, so we subtract 8
                    col = step if step < 8 else step - 8
                    color = 0 # default color
                    if status: # if instrument enabled at that count/step
                        color = DRUM_COLOR[instr_idx] # set color to instrument color
                    trellis.pixels[(row, col)] = color
            elif row in SEQUENCER_ROWS:
                loop_idx = get_loop_index(row, col) # get loop index from button coordinates
                # toggle instrument at loop_idx
                # e.g. if it was previously enabled -> disable & vice-versa
                sequencer[instr_idx][loop_idx] ^= True
                if sequencer[instr_idx][loop_idx]: # if sound was just enabled
                    color = DRUM_COLOR[instr_idx] # grab instrument's color
                else: # if sound was just disabled
                    color = 0 # set color to 0 to turn off the pixel
                trellis.pixels[(row, col)] = color # change color on the board
        current_press = pressed # update current_press
