PORT = 8000

from http.server import BaseHTTPRequestHandler
import socketserver
import json
from readchar import readkey
from sys import argv
from os import environ
from ar_markers import detect_marker
import time

import numpy as np
import cv2

from time import time

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

def cascade(img):
    objs = objs_cascade.detectMultiScale(img, 1.3, 5)
    
    for (x,y,w,h) in objs:
        cv2.rectangle(img, (x,y), (x+w,y+h),(255,0,0),2)
    
    if (x+w)*(y+h) > 100: #사각형이 어느정도 크기 이상이면
        key = 's'
        self.wfile.write(bytes(json.dumps(key), encoding='utf8'))
        self.wfile.write(b'\n')
        '''cv2.waitKey(1)'''
        time.sleep(5)
        key = 'w'
    else:
        key = 'blank'	
    
    return key

def marker(img):
    markers = detect_markers(img)
    for marker in markers:
        print('detected',marker.id)
        marker.highlite_marker(img)
        
    if marker.id == 144:
        key = 'a'
        self.wfile.write(bytes(json.dumps(key), encoding='utf8'))
        self.wfile.write(b'\n')
        '''cv2.waitKey(1)'''
        time.sleep(3)#회전시간
        key = 'w'
        self.wfile.write(bytes(json.dumps(key), encoding='utf8'))
        self.wfile.write(b'\n')
        '''cv2.waitKey(1)'''
        time.sleep(2)#전진시간
    elif marker.id == 922:
        key = 'd'
        self.wfile.write(bytes(json.dumps(key), encoding='utf8'))
        self.wfile.write(b'\n')
        '''cv2.waitKey(1)'''
        time.sleep(3)#회전시간
        key = 'w'
        self.wfile.write(bytes(json.dumps(key), encoding='utf8'))
        self.wfile.write(b'\n')
        '''cv2.waitKey(1)'''
        time.sleep(2)#전진시간
    elif marker.id == 2537:
        key = 's'
    else:
        key = 'blank'

    return key
        
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
        key = 'a'
        self.wfile.write(bytes(json.dumps(key), encoding='utf8'))
        self.wfile.write(b'\n')
        '''cv2.waitKey(1)'''
        time.sleep(5) #유턴하는 시간
	
        key = 'w'
    
    return key

def set_path3(image, forward_criteria):
    height, width = image.shape
    height = height-1
    width = width-1
    center=int(width/2)
    left=0
    right=width        
    
    try:
        '''if image[height][:center].min(axis=0) == 255:
            left = 0
        else:
            left = image[height][:center].argmin(axis=0)    
        if image[height][center:].max(axis=0) == 0:
            right = width
        else:    
            right = center+image[height][center:].argmax(axis=0)  
            q
        center = int((left+right)/2)'''  
        
        print(int(first_nonzero(image[:,center],0,height)))
        forward = min(int(height),int(first_nonzero(image[:,center],0,height))-1)
        #print(height, first_nonzero(image[:,center],0,height))
        
        left_line = first_nonzero(image[height-forward:height,center:],1, width-center)
        right_line = first_nonzero(np.fliplr(image[height-forward:height,:center]),1, center)
        
        center_y = (np.ones(forward)*2*center-left_line+right_line)/2-center
        center_x = np.vstack((np.arange(forward), np.zeros(forward)))
        m, c = np.linalg.lstsq(center_x.T, center_y, rcond=-1)[0]
        if forward < 20 or forward < 50 and abs(m) < 0.35:
            key = 'blank'
        elif abs(m) < forward_criteria:
            key = 'w' 
        elif 2 > m > forward_criteria:
            key = 'q' 
        elif m > 2:
            key = 'a'
        elif 0-forward_criteria > m > -2:
            key = 'e'
        else:
            key = 'd'
    except:
        key = 'x'
        m = 0
    
    return key#, round(m,4), forward

def decision_make(img):
        img=undistort(img)
	
        key = cascade(img)
	
        if key == 'blank':
            key = marker(img)
            if key == 'blank':
                img = select_white(img, 160)
            	key=set_path3(img,0.25)
                if key == 'blank':
                    key = set_path1(img, 160)
			
        return key, img		

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
            
            decision_make(img)

            y1, x1 = img.shape
            x1 = int(x1/2)
            x2 = int(-result[2] * result[1] + x1)
            y2 = y1-result[2] 
            cv2.line(img,(x1,y1),(x2,y2),(255),2)
            cv2.imshow("Processed", img)
            
            
            print(key)
            '''if result[0] == 'forward':
                key="w"
            elif result[0]=='left':
                key="q"
            elif result[0]=='right':
                key="e"
            else:
                key="x"'''
                
            #data = {"action": key}
            print(time(), 'Sending', data)
            self.wfile.write(bytes(json.dumps(key), encoding='utf8'))
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
