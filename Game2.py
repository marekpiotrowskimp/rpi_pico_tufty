from picographics import PicoGraphics, DISPLAY_TUFTY_2040, PEN_RGB332
import time, math, random, gc
from pimoroni import Button
import jpegdec
from machine import Pin, SPI, I2C, UART

from PiicoDev_LIS3DH import PiicoDev_LIS3DH
from PiicoDev_Unified import sleep_ms # cross-platform compatible sleep function

motion = PiicoDev_LIS3DH(0, 100000, machine.Pin(4), machine.Pin(5), 0x18) # Initialise the accelerometer
motion.range = 2 # Set the range to +-2g


display = PicoGraphics(display=DISPLAY_TUFTY_2040, pen_type=PEN_RGB332)
gc.collect()
WIDTH, HEIGHT = display.get_bounds()
print(WIDTH, HEIGHT)
LIGHTEST = display.create_pen(255, 255, 255)
#LIGHT = display.create_pen(160, 168, 64)
#DARK = display.create_pen(112, 128, 40)
DARKEST = display.create_pen(0, 0, 0)

IMAGE_NAME = "eggs.jpg"
BORDER_SIZE = 4
PADDING = 10

from machine import ADC, Pin
from time import sleep

lux_vref_pwr = Pin(27, Pin.OUT)
lux_vref_pwr.value(1)
lux = ADC(26)
vbat_adc = ADC(29)
vref_adc = ADC(28)

def show_photo():
    j = jpegdec.JPEG(display)
    gc.collect()
    # Open the JPEG file
    j.open_file(IMAGE_NAME)
    gc.collect()

    # Draws a box around the image
    #display.set_pen(DARKEST)
    #display.rectangle(PADDING, HEIGHT - ((BORDER_SIZE * 2) + PADDING) - 120, 120 + (BORDER_SIZE * 2), 120 + (BORDER_SIZE * 2))

    # Decode the JPEG
    j.decode(0, 0, jpegdec.JPEG_SCALE_FULL)
    #j.decode() #BORDER_SIZE + PADDING, HEIGHT - (BORDER_SIZE + PADDING) - 120)

    # Draw QR button label
    #display.set_pen(LIGHTEST)
    #display.text("QR", 240, 215, 160, 2)
    
#show_photo()
while True:
    x, y, z = motion.acceleration
    x = round(x,1) # round data for a nicer-looking print()
    y = round(y,1)
    z = round(z,1)
    myString = "X: " + str(x) + ", Y: " + str(y) + ", Z: " + str(z) # build a string of data
    display.set_pen(LIGHTEST)
    display.rectangle(0, 16, 200, 16)
    display.set_pen(DARKEST)
    display.text(myString, 0, 16, 200, 2)
    
    vdd = 1.24 * (65535 / vref_adc.read_u16())
    vbat = ((vbat_adc.read_u16() / 65535) * 3 * vdd)
    display.set_pen(LIGHTEST)
    display.rectangle(0, 0, 200, 16)
    display.set_pen(DARKEST)
    display.text("{:.2f}V".format(vbat) + " {:.2f}V".format(vdd) + " {:.1f}%".format((vbat / vdd) * 100), 0, 0, 200, 2)
    display.update()
    sleep(1)
