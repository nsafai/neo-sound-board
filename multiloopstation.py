import math
import time
import array
import board
import busio
import audioio
import adafruit_trellis_express
import adafruit_adxl34x
from wave_parsing import parse_wav

#################### COLOR SETUP ####################
# four colors for the 4 sounds, using 0 or 255 only will reduce buzz
DRUM_COLOR = ((0, 255, 255),
              (0, 255, 0),
              (255, 255, 0),
              (255, 0, 0) )
              
# the color for the sweeping ticker
TICKER_COLOR = (255, 165, 0)

################### KEYPAD SETUP ####################
# Init keypad with preset settings
trellis = adafruit_trellis_express.TrellisM4Express(rotation=90) # Our keypad + neopixel driver
trellis.pixels._neopixel.brightness = 0.1
# Clear all pixels
trellis.pixels._neopixel.fill(0)
trellis.pixels._neopixel.show()

#################### IMPORT SOUNDS ####################
# Sounds must all:
# - have the same sample rate and must
# - be mono or stereo (no mix-n-match!)
SOUNDS = ["voice01.wav", "voice02.wav", "voice03.wav", "voice04.wav"]
num_sounds = len(SOUNDS)

# Parse the first file to figure out what format its in
wave_format = parse_wav(SOUNDS[0])
print('waveformat: ', wave_format)

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

############# ASSIGN COLORS/SOUNDS TO KEYS ###############
samples = []
# Read the 4 wave files, convert to stereo samples, and store
# (show load status on neopixels and play audio once loaded too!)
for v in range(num_sounds): # for every sound
    for x in range(8):
        # assign same sound to all LEDs in same row
        trellis.pixels[(v, x)] = DRUM_COLOR[v]
        wave_file = open(SOUNDS[v], "rb")
    sample = audioio.WaveFile(wave_file)
    # mixer.play(sample, voice=0)
    while mixer.playing:
        pass # let each sound finish playing before highlighting the other row
    samples.append(sample)
# Clear all pixels
trellis.pixels._neopixel.fill(0)
trellis.pixels._neopixel.show()

################### SEQUENCER SETUP ####################
tempo = 180  # Starting BPM
playing = True
current_step = 7 # we actually start on the last step since we increment first
# the starting state of the sequencer
beatset = [[False] * 8, [False] * 8, [False] * 8, [False] * 8]
current_press = set() # currently pressed buttons


################## TICKER FUNCTIONS ####################
def redrawAfterTicker():
    # redraw the last step to remove the ticker (e.g. show what was there before ticker)
    for y in range(4):
        color = 0 # default value for color if pixel wasn't highlighted
        if beatset[y][current_step]: # if pixel colored before ticket
            color = DRUM_COLOR[y] # grab that color
        trellis.pixels[(y, current_step)] = color # reset color to what it was before

def moveTicker():
    # draw the vertical ticker bar, with selected voices highlighted
    for y in range(4):
        if beatset[y][current_step]:
            r, g, b = DRUM_COLOR[y]
            color = (r//2, g//2, b//2)  # this voice is enabled
            #print("Playing: ", VOICES[y])
            mixer.play(samples[y], voice=y)
        else:
            color = TICKER_COLOR     # no voice on
        trellis.pixels[(y, current_step)] = color


##################### PLAY LOOP ########################
while playing == True:
    stamp = time.monotonic() # stamp represents time at beginning of loop
    redrawAfterTicker() # redraw pixels as they appeared before ticker
    current_step = (current_step + 1) % 8 # next beat!
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

