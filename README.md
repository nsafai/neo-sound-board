# Soundboard
Soundboard uses Python to turn Adafruit's Neotrellis M4 into a loop station.

## Running this locally
- Connect the Neotrellis M4 to your computer
- It will run code.py in the root folder automatically.

## How to debug
- Open your Terminal
- Get Neotrellis USB address using `ls /dev/tty.*` (it'll look like */dev/tty.usbmodem141130*). Copy that value to your clipboard.
- Connect to your Neotrellis using `screen /dev/tty.usbmodem141130 115200` (Note: 115200 is the baud rate.)
- You can find more info [here](https://learn.adafruit.com/adafruit-neotrellis-m4/connecting-to-the-serial-console) if needed

## Where to get more sounds:
https://github.com/adafruit/Adafruit-Sound-Samples 
https://freesound.org/

## Status
Currently in initial phases of development. More will be here soon.
