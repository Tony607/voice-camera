import pyaudio
pa = pyaudio.PyAudio()
_AUDIO_DEVICE_INFO_KEYS = ['index', 'name', 'defaultSampleRate', 'maxInputChannels']
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    if 'usb' in info['name'].lower():
      print('\n\rLocated USB audio input device at index:', info['index'], ', name:', str(info['name']).encode('utf-8'))
    else:
      print('\n\rAudio input device at index:', info.get('index'), ', name:', str(info.get('name')).encode('utf-8'))

pa.terminate()