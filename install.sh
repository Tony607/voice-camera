sudo apt update
# Install dependencies for TensorFlow Object detection API
sudo apt install -y libatlas-base-dev protobuf-compiler python-pil python-lxml python-tk libqtgui4 python-opencv
# Install dependencies for Porcupine
sudo apt install -y libasound-dev portaudio19-dev libportaudio2 libportaudiocpp0 ffmpeg libav-tools
echo "Installing python dependencies"
sudo pip3 install -r ./requirements.txt
# TensorFlow object detection dependencies
echo ">>>> Install finished <<<<"