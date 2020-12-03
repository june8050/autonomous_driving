import time
from picamera.array import PiRGBArray
from picamera import PiCamera
import picamera
from sys import argv
from Time import Time
import cv2
import numpy as np
from time import sleep
import json
from http.client import HTTPConnection
PORT = 8000
file = 'steveholt.jpg'
host = 'localhost'


print(argv)


def Upload(body, headers={}):
    conn = HTTPConnection(f"{argv[1] if len(argv) > 1 else  'localhost'}:{PORT}")
    conn.request('POST', '/', body=body, headers=headers)
    res = conn.getresponse()

    print(res.getheaders())
    print(res.getheader('X-Server2Client', 'Fallback'))
    print(res.read())
    print('Uploaded to', host, 'with status', res.status)


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
        Upload(img.tobytes())


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
