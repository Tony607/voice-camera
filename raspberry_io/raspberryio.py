import sys
import os
if os.uname()[1] == 'raspberrypi':
    from gpiozero import PWMLED

class RaspberryIO(object):
    """Raspberry IO wrapper class.
    """

    def __init__(self, led_pin = 17):
        if 'gpiozero' in sys.modules:
            self._led = PWMLED(led_pin)
        else:
            print("Skip RaspberryIO init")
            self._led = None
    def __del__(self):
        self.led_off()
        del self._led
    def led_pulse(self):
        if self._led is None:
            return
        self._led.pulse()
    def led_blink(self):
        if self._led is None:
            return
        self._led.blink()
    def led_blink_fast(self):
        if self._led is None:
            return
        self._led.blink(0.1, 0.4)
    def led_on(self):
        if self._led is None:
            return
        self._led.on()
    def led_off(self):
        self._led.off()

if __name__ == '__main__':
    io = RaspberryIO()
    io.led_pulse()
    from time import sleep
    sleep(4)
    exit()