import cv2 # For webcam
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from image_processor import ImageProcessor

IM_WIDTH = 640
IM_HEIGHT = 480

detect = ImageProcessor()
detect.setup()
camera = cv2.VideoCapture(0)
if ((camera == None) or (not camera.isOpened())):
    print('\n\n')
    print('Error - could not open video device.')
    print('\n\n')
    exit(0)
ret = camera.set(cv2.CAP_PROP_FRAME_WIDTH,IM_WIDTH)
ret = camera.set(cv2.CAP_PROP_FRAME_HEIGHT,IM_HEIGHT)

# save the actual dimensions
actual_video_width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
actual_video_height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
print('actual video resolution: ' + str(actual_video_width) + ' x ' + str(actual_video_height))

# Initialize frame rate calculation
frame_rate_calc = 1
freq = cv2.getTickFrequency()
font = cv2.FONT_HERSHEY_SIMPLEX

frame_count = 0
while(True):
    t1 = cv2.getTickCount()
    for i in range(5):
        camera.grab()
    ret, frame = camera.read()
    frame_count += 1
    (boxes, scores, classes, num) = detect.detect(frame)
    print('frame:', frame_count)
    cv2.putText(frame,"FPS: {0:.2f} frame: {1}".format(frame_rate_calc, frame_count),(30,50),font,1,(255,255,0),2,cv2.LINE_AA)
    # All the results have been drawn on the frame, so it's time to display it.
    frame = detect.annotate_image(frame, boxes, classes, scores)
    cv2.imshow('Object detector', frame)
    t2 = cv2.getTickCount()
    time1 = (t2-t1)/freq
    frame_rate_calc = 1/time1
    # Press 'q' to quit
    if cv2.waitKey(1) == ord('q'):
        break
    frame_count += 1
camera.release()

cv2.destroyAllWindows()