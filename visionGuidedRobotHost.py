#This program runs on a computer (other than the Pi). It hosts a web socket and recieves image data from the robot.
#It then runs the images through the neural network and returns the command to the robot.

import numpy as np
import socket
import pickle
import tensorflow as tf
import matplotlib.pyplot as plt
import cv2

model = tf.keras.models.load_model("visionGuidedRobotNeuralNetwork.model")
IMG_SIZE = 65
BRIGHTNESS_THRESHOLD = 40
SCANS_PER_TOGGLE = 2

scans = 0
lights_on = False
first_scan = True
commands = []

def load_command(cmd):
    global commands
    MAX_SEND = 3
    commands.append(cmd)
    if len(commands) >= MAX_SEND:
        conn.send(bytes("".join(commands), "utf-8"))
        commands = []

def img_process(img):
    global scans, lights_on, first_scan
    if (scans >= SCANS_PER_TOGGLE and lights_on) or first_scan:
        load_command("lights_off")
        print("Lights disabled")
        lights_on = False
        first_scan = False
        scans = 0
    else:
        load_command("_")
    img_array = np.dot(img[...,:3], [0.299, 0.587, 0.114])
    img_array = cv2.resize(img_array, (IMG_SIZE, IMG_SIZE))
    array = np.array(img_array).reshape(-1, IMG_SIZE, IMG_SIZE, 1)
    scans += 1
    return np.argmax(model.predict(array)), np.mean(array)

def drive(decision):
    global scans, lights_on
    if decision[0] == 1:
        load_command("drive_forward")
        print("drive forward")
    else:
        load_command("turn")
        print("turn")
    if decision[1] < BRIGHTNESS_THRESHOLD and not lights_on:
        load_command("lights_on")
        print("Lights enabled")
        lights_on = True
        scans = 0
    else:
        load_command("_")

#Connect to socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", 12345))
s.listen(1)
print("Server connected")

#Recieve camera data from robot
HEADERSIZE = 10
while True:
    conn, addr = s.accept()
    print(f"Connection from {addr} has been established.")
    full_msg = b""
    new_msg = True
    while True:
        msg = conn.recv(1024)
        if new_msg:
            try:
                msglen = int(msg[:HEADERSIZE])
            except:
                print("Client connection terminated")
                break
            new_msg = False
        full_msg += msg

        if len(full_msg) - HEADERSIZE == msglen:
            img = pickle.loads(full_msg[HEADERSIZE:])
            #Show live camera feed
            cv2.imshow("Robot View", np.array(img, dtype=np.uint8))
            cv2.waitKey(1) & 0xFF
            #Pass camera data into network
            decision = img_process(img)
            #Operate robot based on vision processing
            drive(decision)
            new_msg = True
            full_msg = b""
    cv2.destroyAllWindows()
