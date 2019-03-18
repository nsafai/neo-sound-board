import math
import time
import array
import board
import busio
import audioio
import adafruit_trellis_express
import adafruit_adxl34x
from wave_parsing import parse_wav

tempo = 180  # Starting BPM

# You can use the accelerometer to speed/slow down tempo by tilting!
ENABLE_TILT_TEMPO = True

# You get 4 voices, they must all have the same sample rate and must
# all be mono or stereo (no mix-n-match!)
VOICES = ["voice01.wav", "voice02.wav", "voice03.wav", "voice04.wav"]

# four colors for the 4 voices, using 0 or 255 only will reduce buzz
DRUM_COLOR = ((0, 255, 255),
              (0, 255, 0),
              (255, 255, 0),
              (255, 0, 0) )

# the color for the sweeping ticker
TICKER_COLOR = (255, 255, 255)

# Our keypad + neopixel driver
trellis = adafruit_trellis_express.TrellisM4Express(rotation=90)

# Our accelerometer
i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
accelerometer = adafruit_adxl34x.ADXL345(i2c)

# Parse the first file to figure out what format its in
wave_format = parse_wav(VOICES[0])
print(wave_format)

# Audio playback object - we'll go with either mono or stereo depending on
# what we see in the first file
if wave_format['channels'] == 1:
    audio = audioio.AudioOut(board.A1)
elif wave_format['channels'] == 2:
    audio = audioio.AudioOut(board.A1, right_channel=board.A0)
else:
    raise RuntimeError("All sound files must be either mono or stereo!")
mixer = audioio.Mixer(voice_count=4, sample_rate=wave_format['sample_rate'],
                        channel_count=wave_format['channels'],
                        bits_per_sample=16, samples_signed=True)
audio.play(mixer)

samples = []
# Read the 4 wave files, convert to stereo samples, and store
# (show load status on neopixels and play audio once loaded too!)
for v in range(4):
    for x in range (8):
        trellis.pixels[(v, x)] = DRUM_COLOR[v]
        wave_file = open(VOICES[v], "rb")
    sample = audioio.WaveFile(wave_file)
    mixer.play(sample, voice=0)
    while mixer.playing:
        pass # let each sound finish playing before highlighting the other row
    samples.append(sample)

# Clear all pixels
trellis.pixels._neopixel.fill(0)
trellis.pixels._neopixel.show()

# Our global state
current_step = 7 # we actually start on the last step since we increment first
# the state of the sequencer
beatset = [[False] * 8, [False] * 8, [False] * 8, [False] * 8]
# currently pressed buttons
current_press = set()

while True:
    stamp = time.monotonic()
    # redraw the last step to remove the ticker bar (e.g. 'normal' view)
    for y in range(4):
        color = 0
        if beatset[y][current_step]:
            color = DRUM_COLOR[y]
        trellis.pixels[(y, current_step)] = color

    # next beat!
    current_step = (current_step + 1) % 8
    
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

    # handle button presses while we're waiting for the next tempo beat
    # also check the accelerometer if we're using it, to adjust tempo
    while time.monotonic() - stamp < 60/tempo:
        # Check for pressed buttons
        pressed = set(trellis.pressed_keys)
        #print(pressed)
        for down in pressed - current_press:
            print("Pressed down", down)
            y = down[0]
            x = down[1]
            beatset[y][x] = not beatset[y][x] # enable the voice
            if beatset[y][x]:
                color = DRUM_COLOR[y]
            else:
                color = 0
            trellis.pixels[down] = color
        current_press = pressed

        if ENABLE_TILT_TEMPO:
            # Check accelerometer tilt!
            tilt = accelerometer.acceleration[1]
            #print("%0.1f" % tilt)
            new_tempo = tempo
            if tilt < -9:
                new_tempo = tempo + 5
            elif tilt < -6:
                new_tempo = tempo + 1
            elif tilt > 9:
                new_tempo = tempo - 5
            elif tilt > 6:
                new_tempo = tempo - 1
            if new_tempo != tempo:
                tempo = max(min(new_tempo, 300), 100)
                print("Tempo: %d BPM" % tempo)
                time.sleep(0.05)  # dont update tempo too fast!
        time.sleep(0.01)  # a little delay here helps avoid debounce annoyances
