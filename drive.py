
import numpy as np
import socketio
import eventlet.wsgi
from PIL import Image
from flask import Flask
from io import BytesIO
from scipy.misc import imresize
from keras.models import model_from_json
import argparse
import base64
import json
import numpy as np
import socketio
import eventlet
import eventlet.wsgi
import time
#import utils
from PIL import Image
from PIL import ImageOps
from flask import Flask, render_template
from io import BytesIO
from keras.optimizers import Adam
import csv
import json
import cv2
import numpy as np
import matplotlib.image as mpimg
from PIL import Image
import math



def scale_down(image):
    shape = image.shape
    image = image[math.floor(shape[0]/5):shape[0]-25, 0:shape[1]]
    image = cv2.resize(image,(64,64), interpolation=cv2.INTER_AREA)    
    return image


# Fix error with Keras and TensorFlow
import tensorflow as tf
tf.python.control_flow_ops = tf


sio = socketio.Server()
app = Flask(__name__)
model = None
prev_image_array = None


@sio.on('telemetry')
def telemetry(sid, data):
    # The current steering angle of the car
    steering_angle = data["steering_angle"]
    # The current throttle of the car
    throttle = data["throttle"]
    # The current speed of the car
    speed = data["speed"]
    # The current image from the center camera of the car
    imgString = data["image"]
    image = Image.open(BytesIO(base64.b64decode(imgString)))
    
    test_image = image.convert('RGB')
    image_array = np.asarray(test_image)
    transformed_image_array = image_array[None, :, :, :]
    transformed_image_array = transformed_image_array.reshape(transformed_image_array.shape[1:]) # Get the following shape (64, 64, 3) instead of (1, 64, 64, 3)
    test_image = scale_down(transformed_image_array)
    
    # This model currently assumes that the features of the model are just the images. Feel free to change this.
    test_image = test_image[np.newaxis,:] # Add one dimension to get (1, :, :, :)
    steering_angle = float(model.predict(test_image, batch_size=1))
    # The driving model currently just outputs a constant throttle. Feel free to edit this.
    throttle = 0.2 #.32 for track 2
    print(steering_angle, throttle)
    send_control(steering_angle, throttle) # steering_angle*1.4 for track 2

@sio.on('connect')
def connect(sid, environ):
    print("connect ", sid)
    send_control(0, 0)


def send_control(steering_angle, throttle):
    sio.emit("steer", data={
        'steering_angle': steering_angle.__str__(),
        'throttle': throttle.__str__()
    }, skip_sid=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Remote Driving')
    parser.add_argument('model', type=str,
    help='Path to model definition json. Model weights should be on the same path.')
    args = parser.parse_args()
    with open(args.model, 'r') as jfile:
        model = model_from_json(jfile.read())

    model.compile("adam", "mse")
    weights_file = args.model.replace('json', 'h5')
    model.load_weights(weights_file)

    # wrap Flask application with engineio's middleware
    app = socketio.Middleware(sio, app)

    # deploy as an eventlet WSGI server
    eventlet.wsgi.server(eventlet.listen(('', 4567)), app)

