import math
import time
import array
import board
import busio
import audioio
import adafruit_trellis_express
import adafruit_adxl34x
from wave_parsing import parse_wav
import os
import random


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
    # use this fn to get index of button from their (col, row) coordinates
    return col * NUM_INSTR_ROWS + row

def get_loop_index(row, col):
    return col * NUM_SEQ_ROWS + row


#################### IMPORT SOUNDS ####################
# Sounds must all (1) have the same sample rate and (2) be mono or stereo (no mix-n-match!)
SOUNDS = []
# go through every file in /sounds directory
for file in os.listdir("/sounds"):
    # get all .wav files but ignore files that start with "."
    if file.endswith(".wav") and not file.startswith("."):
        # append those to SOUNDS
        SOUNDS.append("/sounds/" + str(file))
# print(SOUNDS)
num_sounds = len(SOUNDS)

# Parse the first file to figure out what format its in
wave_format = parse_wav(SOUNDS[0])
# print('waveformat: ', wave_format)

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
# leaving 16 buttons for sounds
for col in range(8): # across 8 columns
    for row in range(2): # across 2 rows
        # generate a random color (TODO: make this smarter)
        random_color = random.randint(cur_idx, 0xFFFFFF)
        DRUM_COLOR.append(random_color) # append drum color
        trellis.pixels[(row, col)] = DRUM_COLOR[cur_idx] # assign color on trellis
        wave_file = open(SOUNDS[cur_idx], "rb") # open the corresponding wave file
        sample = audioio.WaveFile(wave_file) # convert wave file
        # mixer.play(sample, voice=0) # play random sample
        # while mixer.playing:
        #     pass # let each sound finish playing before highlighting the other row
        samples.append(sample) # append to list of sound samples
        sequencer.append([False] * 16) # starting state of sequencer for all instruments
        cur_idx += 1 # iterate cur_idx
mixer.play(random.choice(samples), voice=0) # play random sample


################## TICKER FUNCTIONS ####################
def redraw_after_ticker():
    # redraw the last step to remove the ticker (e.g. show what was there before ticker)
    # row is 3 (top row) for first 8 counts, then 2 (second row)
    row = 3 if current_step < 8 else 2
    # current_step (0-15) but col can only be equal to 0-7
    col = current_step if current_step < 8 else (current_step - 8)
    color = 0
    # TODO: if beatset[y][current_step]: # if pixel colored before ticker
        # color = DRUM_COLOR[y] # grab that color
    trellis.pixels[(row, col)] = color

def move_ticker():
    # draw the ticker for every count, where loop_size = 16 counts
    # row is 3 (top row) for first 8 counts, then 2 (second row)
    row = 3 if current_step < 8 else 2
    # current_step (0-15) but col can only be equal to 0-7
    col = current_step if current_step < 8 else (current_step - 8)
    # TODO: if there are sounds at ticker coordinate, show slightly different color
    # TODO: if there are sounds at ticker coordinate, play those sounds 
        #     if beatset[y][current_step]:
        #         r, g, b = DRUM_COLOR[y]
        #         color = (r//2, g//2, b//2)  # this voice is enabled
        #         #print("Playing: ", VOICES[y])
        #         mixer.play(samples[y], voice=y)
    trellis.pixels[(row, col)] = TICKER_COLOR


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
            print("Pressed down", btn)
            row, col = btn[0], btn[1] # unwrap coordinates of pressed button
            if row in INSTR_ROWS:
                instr_idx = get_instr_index(row, col)
                print('instrument index:', instr_idx)
                # play sound of button pressed
                mixer.play(samples[instr_idx], voice=0) 
            elif row in SEQUENCER_ROWS:
                loop_idx = get_loop_index(row, col)
                print('want to add instrument:', instr_idx, 'at loop index:', loop_idx)
            # toggle sound of pressed button (i.e. if it was previously enabled -> disable)
            # beatset[y][x] = not beatset[y][x]
            # if beatset[y][x]: # if sound was just enabled
                # color = DRUM_COLOR[y] # grab appropriate color
            # else: # if sound was just disabled
            #     color = 0 # set color to 0 to turn off the pixel
            # trellis.pixels[btn] = color # change color on the board
        current_press = pressed # update current_press

