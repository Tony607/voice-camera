#
# Copyright 2018 Picovoice Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

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


class PorcupineDemo(Thread):
    """
    Demo class for wake word detection (aka Porcupine) library. It creates an input audio stream from a microphone,
    monitors it, and upon detecting the specified wake word(s) prints the detection time and index of wake word on
    console. It optionally saves the recorded audio into a file for further review.
    This is the non-blocking version that uses the callback function of PyAudio.
    """

    def __init__(
            self,
            library_path,
            keywords = None,
            sensitivity=0.5,
            input_device_index=None,
            output_path=None):

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
        if input_device_index is None:
            input_device_index = self.locate_usb_audio_device()
        self._library_path = library_path
        self._keywords = keywords
        self._sensitivity = float(sensitivity)
        self._input_device_index = input_device_index

        self._output_path = output_path
        if self._output_path is not None:
            self._recorded_frames = []

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

            while True:
                time.sleep(0.1)

        except KeyboardInterrupt:
            print('stopping ...')
        finally:
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
