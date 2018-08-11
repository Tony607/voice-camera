sudo apt update
sudo apt install libatlas-base-dev protobuf-compiler python-pil python-lxml python-tk libqtgui4 python-opencv
echo "Installing python dependencies"
sudo pip3 install -r ./requirements.txt
# TensorFlow object detection dependencies
echo ">>>> Install finished <<<<"