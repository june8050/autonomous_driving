PORT = 8000

from http.server import BaseHTTPRequestHandler
import socketserver
import json
from readchar import readkey
from sys import argv
from os import environ
from ar_markers import detect_markers
from time import sleep
from time import time
import numpy as np
import cv2

httpd = None
DISPLAY = 'DISPLAY' in environ
DISPLAY=True

map1 = np.load('./map1.npy')
map2 = np.load('./map2.npy')

objs_cascade = cv2.CascadeClassifier('./cascade.xml')

def select_white(image, white):
    lower = np.uint8([white,white,white])
    upper = np.uint8([255,255,255])
    white_mask = cv2.inRange(image, lower, upper)
    return white_mask

def undistort(img):
    
    h,w = img.shape[:2]
    
    undistorted_img=cv2.remap(img, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    
    return undistorted_img

def detect(cascade_classifier, image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    result = 'blank'         
    # scale Factor : 1 초과의 값, 1에 가까울 수록 연산량이 많아짐
    # minNeighbors : 0에 가까울수록 더 많은 물체를 잡음 (더 많이 틀림)
    # minSize : 최소 크기 - 너무 먼 물체를 잡는 문제를 해결하기 위함
    cascade_obj = cascade_classifier.detectMultiScale(
        gray_image,
        scaleFactor=1.02,
        minNeighbors=5,
        minSize=(16,16),           
    )
        
    # 잡힌 물체들 목록이  cascade_obj'
    # 이 예제에서는 굳이 40, 40 이상을 따로 구분해서 표시함
    # 16~40 사이의 물체는 인식은 되는데 그려주지는 않음. 단지 width height를 확인하는 용도
    # 크기를 체크하면서 최적 값을 찾는 흔적으로 보임.
    for (x_pos, y_pos, width, height) in cascade_obj:
        # draw a rectangle around the objects
        #print(width,height)
        if(width>=40):
            cv2.rectangle(image, (x_pos, y_pos), (x_pos+width, y_pos+height), (255, 255, 255), 2)
            cv2.putText(image, 'Stop', (x_pos, y_pos-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            result = "detected"
        else:
            result = 'blank'    
    return result

def marker(img):
    id = []
    markers = detect_markers(img)
    for marker in markers:
        id.append(marker.id)
    
       
    return id

def first_nonzero(arr, axis, invalid_val=-1):
    arr = np.flipud(arr)
    mask = arr!=0
    return np.where(mask.any(axis=axis), mask.argmax(axis=axis), invalid_val)

def set_path1(image, upper_limit, fixed_center = 'False', sample=10):
    height, width = image.shape
    height = height-1
    width = width-1
    center=int(width/2)
    left=0
    right=width
    white_distance = np.zeros(width)

    if not fixed_center: 
        for i in range(center):
            if image[height,center-i] > 200:
                left = center-i
                break            
        for i in range(center):
            if image[height,center+i] > 200:
                right = center+i
                break    
        center = int((left+right)/2)      

    for i in range(left,right,sample):
        for j in range(upper_limit):
            if image[height-j,i] > 200:                
                white_distance[i]=j
                break
    
    left_sum = np.sum(white_distance[left:center])
    right_sum = np.sum(white_distance[center:right])
    
    sum = left_sum + right_sum
    
    if sum < 2000:
        result = 'turn'
    else:
        result = 'x'
    
    return result

def set_path3(image, forward_criteria):
    height, width = image.shape
    height = height-1
    width = width-1
    center=int(width/2)
    left=0
    right=width        
    
    try:
        print(int(first_nonzero(image[:,center],0,height)))
        forward = min(int(height),int(first_nonzero(image[:,center],0,height))-1)
        #print(height, first_nonzero(image[:,center],0,height))
        
        left_line = first_nonzero(image[height-forward:height,center:],1, width-center)
        right_line = first_nonzero(np.fliplr(image[height-forward:height,:center]),1, center)
        
        center_y = (np.ones(forward)*2*center-left_line+right_line)/2-center
        center_x = np.vstack((np.arange(forward), np.zeros(forward)))
        m, c = np.linalg.lstsq(center_x.T, center_y, rcond=-1)[0]
        if forward < 20 or forward < 50 and abs(m) < 0.35:
            result = set_path1(image,160)
        elif abs(m) < forward_criteria:
            result = 'w' 
        elif 2 > m > forward_criteria:
            result = 'q' 
        elif m > 2:
            result = 'a'
        elif 0-forward_criteria > m > -2:
            result = 'e'
        else:
            result = 'd'
    except:
        result = 'x'
        m = 0
        

    return result #, round(m,4), forward


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','application/json')
        self.end_headers()

        print("Write to stdin")
        while True:
            key = readkey()
            if key == '\x03':
                break

            data = {"action": key}
            print(time(), 'Sending', data)
            self.wfile.write(
                bytes(json.dumps(data), encoding='utf8'))
            self.wfile.write(b'\n')

        self.finish()
        httpd.shutdown()


    def do_POST(self):
        print(self.headers['X-Client2Server'])

        self.send_response(200)
        self.send_header('X-Server2Client', '123')
        self.end_headers()

        data = self.rfile.read(int(self.headers['Content-Length']))
        if DISPLAY:
            data = np.asarray(bytearray(data), dtype="uint8")
            img = cv2.imdecode(data, cv2.IMREAD_ANYCOLOR)
            
            img= undistort(img)
            white_image = select_white(img, 160)

            cascade_result = detect(objs_cascade,img)
            marker_result = marker(img)
            key = set_path3(white_image,0.25)
              
            data = {"key": key, 'cascade':cascade_result, 'marker':marker_result}
            print(time(), 'Sending', data)
            self.wfile.write(bytes(json.dumps(data), encoding='utf8'))
            self.wfile.write(b'\n')
            #cv2.imshow('image', img)
            cv2.waitKey(1)

        else:
            with open('uploaded.jpg', 'wb') as File:
                File.write(data)
                print('Written to file')

        #self.wfile.write(bytes(json.dumps({"foo": "bar"}), encoding='utf8'))



with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as _httpd:
    httpd = _httpd
    print("HTTPServer Serving at port", PORT)
    httpd.serve_forever()
