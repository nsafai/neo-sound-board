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
trellis.pixels._neopixel.brightness = 0.1
# Clear all pixels
trellis.pixels._neopixel.fill(0)
trellis.pixels._neopixel.show()


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
        mixer.play(sample, voice=0) # play sample
        # while mixer.playing:
        #     pass # let each sound finish playing before highlighting the other row
        samples.append(sample) # append to list of sound samples
        cur_idx += 1 # iterate cur_idx
# Clear all pixels
trellis.pixels._neopixel.fill(0)
trellis.pixels._neopixel.show()


################### SEQUENCER SETUP ####################
tempo = 180  # Starting BPM
playing = True
current_step = 15 # we actually start on the last step since we increment first
# the starting state of the sequencer
beatset = [[False] * 8, [False] * 8, [False] * 8, [False] * 8]
current_press = set() # currently pressed buttons


################## TICKER FUNCTIONS ####################
def redrawAfterTicker():
    # redraw the last step to remove the ticker (e.g. show what was there before ticker)
    if current_step < 8:
      row = 3
      col = current_step
    else:
      row = 2
      col = current_step - 8
    color = 0
    # if beatset[y][current_step]: if pixel colored before ticker
        # color = DRUM_COLOR[y] # grab that color
    trellis.pixels[(row, col)] = color
    print('turning off', row, 'col', col)
    # for y in range(4):
    #     color = 0 # default value for color if pixel wasn't highlighted
    #     if beatset[y][current_step]: # if pixel colored before ticker
    #         color = DRUM_COLOR[y] # grab that color
    #     trellis.pixels[(y, current_step)] = color # reset color to what it was before

def moveTicker():
    # draw the ticker for every count, where loop_size = 16 counts
    if current_step < 8:
      row = 3
      col = current_step
    else:
      row = 2
      col = current_step - 8
    # TODO: if there are sounds at ticker coordinate, show slightly different sound
    print('turning on row', row, 'col', col)
    trellis.pixels[(row, col)] = TICKER_COLOR
    # mixer.play(samples_at_index)
    # for y in range(4):
    #     if beatset[y][current_step]:
    #         r, g, b = DRUM_COLOR[y]
    #         color = (r//2, g//2, b//2)  # this voice is enabled
    #         #print("Playing: ", VOICES[y])
    #         mixer.play(samples[y], voice=y)
    #     else:
    #         color = TICKER_COLOR     # no voice on
    #     trellis.pixels[(y, current_step)] = color


##################### PLAY LOOP ########################
while playing == True:
    stamp = time.monotonic() # stamp represents time at beginning of loop
    redrawAfterTicker() # redraw pixels as they appeared before ticker
    current_step = (current_step + 1) % 16 # next beat!
    moveTicker() # move yellow ticker
    # handle button presses while we're waiting for the next tempo beat
    while time.monotonic() - stamp < 60/tempo:
        # grab currently pressed buttons
        pressed = set(trellis.pressed_keys) 
        # for every button pressed:
        for down in pressed - current_press:
            print("Pressed down", down)
            y, x = down[0], down[1] # unwrap coordinates of each pressed button
            # toggle sound of pressed button (i.e. if it was previously enabled -> disable)
            beatset[y][x] = not beatset[y][x]
            if beatset[y][x]: # if sound was just enabled
                color = DRUM_COLOR[y] # grab appropriate color
            else: # if sound was just disabled
                color = 0 # set color to 0 to turn off the pixel
            trellis.pixels[down] = color # change color on the board
        current_press = pressed # update current_press

