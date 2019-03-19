import adafruit_trellis_express
# Our keypad + neopixel driver
trellis = adafruit_trellis_express.TrellisM4Express(rotation=90)
trellis.pixels._neopixel.brightness = 0.1
# Clear all pixels
trellis.pixels._neopixel.fill(0)
trellis.pixels._neopixel.show()