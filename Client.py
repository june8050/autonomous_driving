import time
from picamera.array import PiRGBArray
from picamera import PiCamera
import picamera
from sys import argv
from time import time
import cv2
import numpy as np
from time import sleep
import json
from http.client import HTTPConnection
import RPi.GPIO as GPIO
PORT = 8000
file = 'steveholt.jpg'
host = 'localhost'

print(argv)

 # pin definition
motor1A = 16
motor1B = 18
motor2A = 22
motor2B = 24

# pin setting
GPIO.setmode(GPIO.BOARD)
GPIO.setup(motor1A, GPIO.OUT)
GPIO.setup(motor1B, GPIO.OUT)
GPIO.setup(motor2A, GPIO.OUT)
GPIO.setup(motor2B, GPIO.OUT)

# PWM
p1A = GPIO.PWM(motor1A, 1000)
p1B = GPIO.PWM(motor1B, 1000)
p2A = GPIO.PWM(motor2A, 1000)
p2B = GPIO.PWM(motor2B, 1000)
p1A.start(0)
p1B.start(0)
p2A.start(0)
p2B.start(0)
    
HALF = .5
MOTOR_SPEEDS = {
    "c": [0, 100, 0, 50], "x": [0, 100, 0, 100], "z": [0, 50, 0, 100],
    "a": [0, 100, 100, 0], "s": [100, 100, 100, 100], "d": [100, 0, 0, 100],
    "e": [100, 0, 50, 0], "w": [100, 0, 100, 0], "q": [50, 0, 100, 0],
}


def Upload(body, headers={}):
    conn = HTTPConnection(f"{argv[1] if len(argv) > 1 else  'localhost'}:{PORT}")
    conn.request('POST', '/', body=body, headers=headers)
    res = conn.getresponse()

    print(res.getheaders())
    print(res.getheader('X-Server2Client', 'Fallback'))
    print('Uploaded to', host, 'with status', res.status)
    return res.read()


def Camera():
    camera = PiCamera()
    camera.resolution = (320, 240)
    camera.vflip = True
    camera.hflip = True
    camera.framerate = 30

    return camera


def UploadCamera(camera, rawCapture):
    for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
        img = frame.array
        print('shape', img.shape)
        result, img = cv2.imencode(
            '.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not result:
            raise Exception('Image encode error')

        rawCapture.truncate(0)
        data = Upload(img.tobytes())
        data = json.loads(data)
        print(time(), data)
        #action = data['action']
        #print('action', action)
                          
        #초음파

        direction = MOTOR_SPEEDS[data]

        a = direction[0]
        b = direction[1]
        c = direction[2]
        d = direction[3]

        p1A.ChangeDutyCycle(a)
        p1B.ChangeDutyCycle(b)
        p2A.ChangeDutyCycle(c)
        p2B.ChangeDutyCycle(d)


def main():
    camera = Camera()
    rawCapture = PiRGBArray(camera, size=(320, 240))

    

    while True:
        try:
            UploadCamera(camera, rawCapture)

        except ConnectionRefusedError as error:
            print(error)
            sleep(1)


main()
