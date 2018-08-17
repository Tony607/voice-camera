from ThermalPrinter import Adafruit_Thermal

_printer = Adafruit_Thermal("/dev/ttyUSB0", 115200)
img = './data/paint.png'
_printer.printImage(img, LaaT=True, reverse = False, rotate=True, auto_resize = True)
_printer.feed(2)
