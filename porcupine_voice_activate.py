import argparse
import os
import platform
import struct
import sys
import time
from datetime import datetime
from threading import Thread

import numpy as np
import pyaudio
import soundfile

from porcupine import Porcupine
from ThermalPrinter import Adafruit_Thermal

import cv2 # For webcam
from image_processor import ImageProcessor
from drawing_dataset import DrawingDataset
from sketch import SketchGizeh
from PIL import Image

from raspberry_io import RaspberryIO

class PorcupineDemo(Thread):
    """
    Demo class for wake word detection (aka Porcupine) library. It creates an input audio stream from a microphone,
    monitors it, and upon detecting the specified wake word(s) prints the detection time and index of wake word on
    console. It optionally saves the recorded audio into a file for further review.
    This is the non-blocking version that uses the callback function of PyAudio.
    """
    # Set up camera constants
    IM_WIDTH = 640
    IM_HEIGHT = 480
    def __init__(
            self,
            library_path,
            keywords = None,
            sensitivity=0.5,
            input_device_index=None,
            output_path=None,
            printer_serial_port = "/dev/ttyUSB0",
            printer_baudrate = 115200,
            ):

        """
        Constructor.

        :param library_path: Absolute path to Porcupine's dynamic library.
        :param sensitivity: Sensitivity parameter. For more information refer to 'include/pv_porcupine.h'. It uses the
        same sensitivity value for all keywords.
        :param input_device_index: Optional argument. If provided, audio is recorded from this input device. Otherwise,
        the default audio input device is used.
        :param output_path: If provided recorded audio will be stored in this location at the end of the run.
        """

        super(PorcupineDemo, self).__init__()
        self.io = RaspberryIO(callback=self.setPendingPrint)
        # Blink LED fast to show the programming is loading.
        self.io.led_blink_fast()
        if input_device_index is None:
            input_device_index = self.locate_usb_audio_device()
        self._library_path = library_path
        self._keywords = keywords
        self._sensitivity = float(sensitivity)
        self._input_device_index = input_device_index

        self._output_path = output_path
        if self._output_path is not None:
            self._recorded_frames = []
            
        self._printer = Adafruit_Thermal(printer_serial_port, printer_baudrate)
        self._pendingPrint = False
        self._pendingEdgePrint = False
        self.detect = ImageProcessor()
        self.detect.setup()
        self.dataset = DrawingDataset('./data/quick_draw_pickles/', './data/label_mapping.jsonl')
        self.dataset.setup()
        self.sk = SketchGizeh()

    def run(self):
        """
        Creates an input audio stream, initializes wake word detection (Porcupine) object, and monitors the audio
        stream for occurrences of the wake word(s). It prints the time of detection for each occurrence and index of
        wake word.
        """

        num_keywords = len(self._keywords)
        def _audio_callback(in_data, frame_count, time_info, status):
            if frame_count >= porcupine.frame_length:
                pcm = struct.unpack_from("h" * porcupine.frame_length, in_data)
                result = porcupine.process(pcm)
                if num_keywords == 1 and result:
                    print('[%s] detected keyword' % str(datetime.now()))
                    # add your own code execution here ... it will not block the recognition
                elif num_keywords > 1 and result >= 0:
                    print('[%s] detected %s' % (str(datetime.now()), self._keywords[result]))
                    if result == 0:
                        self._pendingPrint = True
                    elif result == 1:
                        self._pendingEdgePrint = True
                    # or add it here if you use multiple keywords

                if self._output_path is not None:
                    self._recorded_frames.append(pcm)
            
            return None, pyaudio.paContinue

        porcupine = None
        pa = None
        audio_stream = None
        sample_rate = None
        try:
            porcupine = Porcupine(
                library_path=self._library_path,
                keywords=self._keywords,
                sensitivities=[self._sensitivity] * num_keywords)

            pa = pyaudio.PyAudio()
            sample_rate = porcupine.sample_rate
            num_channels = 1
            audio_format = pyaudio.paInt16
            frame_length = porcupine.frame_length
            
            audio_stream = pa.open(
                rate=sample_rate,
                channels=num_channels,
                format=audio_format,
                input=True,
                frames_per_buffer=frame_length,
                input_device_index=self._input_device_index,
                stream_callback=_audio_callback)

            audio_stream.start_stream()

            print("Started porcupine with following settings:")
            if self._input_device_index:
                print("Input device: %d (check with --show_audio_devices_info)" % self._input_device_index)
            else:
                print("Input device: default (check with --show_audio_devices_info)")
            print("Sample-rate: %d" % sample_rate)
            print("Channels: %d" % num_channels)
            print("Format: %d" % audio_format)
            print("Frame-length: %d" % frame_length)
            print("Keywords: %s" % self._keywords)
            print("Waiting for keywords ...\n")
            # Pulse LED to show the Pi is ready for voice command.
            self.io.led_pulse()
            while True:
                if self._pendingPrint is True:
                    # LED on to show the Pi is taking photos.
                    self.io.led_on()
                    self.run_camera()
                    self._pendingPrint = False
                    # Pulse LED to show the Pi is ready for voice command.
                    self.io.led_pulse()
                if self._pendingEdgePrint is True:
                    # LED on to show the Pi is taking photos.
                    self.io.led_on()
                    self.run_edge_camera()
                    self._pendingEdgePrint = False
                    # Pulse LED to show the Pi is ready for voice command.
                    self.io.led_pulse()

                time.sleep(0.1)

        except KeyboardInterrupt:
            print('stopping ...')
        finally:
            del self.io
            if audio_stream is not None:
                audio_stream.stop_stream()
                audio_stream.close()

            if pa is not None:
                pa.terminate()

            # delete Porcupine last to avoid segfault in callback.
            if porcupine is not None:
                porcupine.delete()

            if self._output_path is not None and sample_rate is not None and len(self._recorded_frames) > 0:
                recorded_audio = np.concatenate(self._recorded_frames, axis=0).astype(np.int16)
                soundfile.write(self._output_path, recorded_audio, samplerate=sample_rate, subtype='PCM_16')
    
    def setPendingPrint(self):
        self._pendingPrint=True

    def run_camera(self):
        camera = cv2.VideoCapture(0)
        if ((camera == None) or (not camera.isOpened())):
            print('\n\n')
            print('Error - could not open video device.')
            print('\n\n')
            exit(0)
        ret = camera.set(cv2.CAP_PROP_FRAME_WIDTH,self.IM_WIDTH)
        ret = camera.set(cv2.CAP_PROP_FRAME_HEIGHT,self.IM_HEIGHT)
        # save the actual dimensions
        actual_video_width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_video_height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print('actual video resolution: ' + str(actual_video_width) + ' x ' + str(actual_video_height))
        frame_count = 0
        while(True):
            for i in range(5):
                camera.grab()
            ret, frame = camera.read()
            frame_count += 1
            (boxes, scores, classes, num) = self.detect.detect(frame)
            # save image
            # cv2.imwrite('./image.jpg', frame)
            self.sk.setup()
            drawn_objects = self.sk.draw_object_recognition_results(np.squeeze(boxes),
                                            np.squeeze(classes).astype(np.int32),
                                            np.squeeze(scores),
                                            self.detect.labels,
                                            self.dataset)
            print('frame:', frame_count)
            if len(drawn_objects) > 0:
                camera.release()
                print(drawn_objects)
                img = Image.fromarray(self.sk.get_npimage())
                self._printer.printImage(img, LaaT=True, reverse = False, rotate=True, auto_resize = True)
                self._printer.feed(2)
                break

    def run_edge_camera(self):
        camera = cv2.VideoCapture(0)
        if ((camera == None) or (not camera.isOpened())):
            print('\n\n')
            print('Error - could not open video device.')
            print('\n\n')
            exit(0)
        ret = camera.set(cv2.CAP_PROP_FRAME_WIDTH,self.IM_WIDTH)
        ret = camera.set(cv2.CAP_PROP_FRAME_HEIGHT,self.IM_HEIGHT)
        # save the actual dimensions
        actual_video_width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_video_height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print('actual video resolution: ' + str(actual_video_width) + ' x ' + str(actual_video_height))
        for i in range(5):
            camera.grab()
        ret, frame = camera.read()
        camera.release()
        frame = cv2.Canny(frame,210, 100)
        kernel = np.ones((2,2),np.uint8)
        frame = cv2.dilate(frame,kernel,iterations = 2)
        img = Image.fromarray(frame)
        self._printer.printImage(img, LaaT=True, reverse = True, rotate=True, auto_resize = True)
        self._printer.feed(2)

    _AUDIO_DEVICE_INFO_KEYS = ['index', 'name', 'defaultSampleRate', 'maxInputChannels']

    @classmethod
    def locate_usb_audio_device(cls):
        pa = pyaudio.PyAudio()
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if 'usb' in info['name'].lower():
                print('\n\rLocated USB audio input device at index:', info['index'], ', name:', str(info['name']).encode('utf-8'))
                pa.terminate()
                return info['index']
        pa.terminate()
        print('\n\rNo USB audio input device found.')
        return None

    @classmethod
    def show_audio_devices_info(cls):
        """ Provides information regarding different audio devices available. """

        pa = pyaudio.PyAudio()

        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            print(', '.join("'%s': '%s'" % (k, str(info[k])) for k in cls._AUDIO_DEVICE_INFO_KEYS))

        pa.terminate()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--keyword_file_paths', help='comma-separated absolute paths to keyword files', type=str, default=None)
    parser.add_argument('--keywords', help='comma-separated absolute keywords text', type=str, default=None)

    parser.add_argument(
        '--library_path',
        help="absolute path to Porcupine's dynamic library",
        type=str)

    parser.add_argument('--sensitivity', help='detection sensitivity [0, 1]', default=0.5)
    parser.add_argument('--input_audio_device_index', help='index of input audio device', type=int, default=None)

    parser.add_argument(
        '--output_path',
        help='absolute path to where recorded audio will be stored. If not set, it will be bypassed.',
        type=str,
        default=None)

    parser.add_argument('--show_audio_devices_info', action='store_true')

    args = parser.parse_args()

    if args.show_audio_devices_info:
        PorcupineDemo.show_audio_devices_info()
    else:
        if not args.keywords:
            raise ValueError('keywords must be defined.')
        PorcupineDemo(
            library_path=args.library_path,
            keywords = [x.strip() for x in args.keywords.split(',')],
            sensitivity=args.sensitivity,
            output_path=args.output_path,
            input_device_index=args.input_audio_device_index
        ).run()
