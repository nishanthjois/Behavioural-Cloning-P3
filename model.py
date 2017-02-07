# Udacity SDND's project 3: Use Deep Learning to Clone Driving Behaviour
# Author: Nishanth Jois

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from scipy.misc import imread, imresize
from matplotlib import pyplot as plt
from keras.layers import BatchNormalization, Conv2D, Dense, Flatten, Dropout, MaxPooling2D,Lambda,Convolution2D,ELU
from keras.layers.core import Dense, Dropout, Activation, Flatten, Lambda
from keras.callbacks import Callback, ModelCheckpoint, EarlyStopping
from keras.preprocessing.image import ImageDataGenerator
from keras.optimizers import Adam
from sklearn.model_selection import train_test_split
from keras.models import Sequential, model_from_json
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.preprocessing.image import *
import cv2
import csv, random, numpy as np
from sklearn.utils import shuffle
from IPython.display import display
import time
import shutil
import os
import random
import cv2
import math
import json
import keras
import matplotlib.pyplot as plt
# %matplotlib inline

# Read csv file and store as panda's data frame
df = pd.read_csv('driving_log_1.csv')
#print (df.head(2))

# Read input file column wise - output will have image paths and angles
def read_csv(df):
    image_paths = pd.concat([df['center'], df['left'], df['right']])
    image_paths = np.array(image_paths, dtype=pd.Series)
    
# As the training data has more left turns than right - additional data is generated by mirroring center images 
# and adding a negative steering angle for the same

    mirror_paths = df['center']
    mirror_paths = np.array(mirror_paths, dtype=pd.Series)
    
    paths= np.append(image_paths,mirror_paths)
    
# +/- 0.2 is added to steering angle to compensate for the turn, e.g.,
# left camera has to move to +0.2 towards right to get center
    angles = pd.concat([df['steering'], df['steering'] + 0.25, df['steering'] - 0.25,-df['steering']])
    angles = np.array(angles, dtype=pd.Series)
    
    return paths, angles

X,y=read_csv(df)

#Shuffle training data
X, y = shuffle(X,y, random_state=7)
# print ('Number of images:', len(X))
# print ('Number of images:', len(y))

# Data is split into trainig and validation data into 80:20 format (i.e., test size = 0.2)
#We are not spliting data for testing purpose as testing will be done on simulator
images_training, images_validation, angles_training, angles_validation = train_test_split(X, y, test_size=0.2, random_state=7)


#Constants
rows,cols = 64,64 # image size
wShift = 100 # width shift
hShift = 40 # height shift

# Read images from path and then augment images
def load_process_image(path, steering_angle):
    path = path.replace(' ', '')
    img = imread(path)
    img, steering_angle = augment_image(img, steering_angle)
    return img, steering_angle

#helper function for augmentation
def augment_image (img, steering_angle):
    transformed_image, steering_angle = height_width_augmentation(img, steering_angle)
    transformed_image = brightness_augmentation(transformed_image)          
    transformed_image = crop_resize_image(transformed_image)
    return transformed_image, steering_angle

# Shift height and width by a small margin to simulate car being at different postions (left/right and up/down)
# After shifting we will add corresponding steering angles
def height_width_augmentation(img, steering_angle):
    rows, cols, channels = img.shape
    
    # Translation
    tx = wShift * np.random.uniform() - wShift / 2
    ty = hShift * np.random.uniform() - hShift / 2
    steering_angle = steering_angle + tx / wShift * 2 * .2
    
    transform_matrix = np.float32([[1, 0, tx],
                                   [0, 1, ty]])
    
    translated_image = cv2.warpAffine(img, transform_matrix, (cols, rows))
    return translated_image, steering_angle

# Add random brightness to simulate car 
# being in different lighting conditions (sunlight, shadow, dawn/dusk, steertlight, etc.,)
# http://docs.opencv.org/3.1.0/da/d6e/tutorial_py_geometric_transformations.html
def brightness_augmentation(img, bright_value=None):
    img = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    
    if bright_value:
        img[:,:,2] += bright_value
    else:
        random_bright = .25 + np.random.uniform()
        img[:,:,2] = img[:,:,2] * random_bright
    
    img = cv2.cvtColor(img, cv2.COLOR_HSV2RGB)
    return img

# Crop sky and car's hood (Note: we should use same cropping again in drive.py else car wont start)
def crop_resize_image(img):
    shape = img.shape
    img = img[math.floor(shape[0]/5):shape[0]-25, 0:shape[1]]
    img = cv2.resize(img, (rows, cols), interpolation=cv2.INTER_AREA) # 64 * 64  
    return img

# Python's generator:
# Generates batch of images and steering angles by using Python's yield
# Reason for using generator is to reduce memory overhead as we are dealing with more than 20K images
def data_generator(X,y,batch_size):
  
    while 1:
        batch_images = []
        batch_steering = []
        for i_batch in range(batch_size):
            j = random.randint(0, len(X) - 1)
            images,angles  = load_process_image(X[j],y[j]) #returns an agumented image          
            batch_images.append(images)
            batch_steering.append(angles)
            
            img = np.array(batch_images)
            angle = np.array(batch_steering)
            
        yield img,angle
        
# Training model:
#   Ref: https://devblogs.nvidia.com/parallelforall/deep-learning-self-driving-cars/
#     1. Nvidia model (almost similar) is used with input image size as 64*64
#     2. First layer is normalization layer
#     3. Model consists of 5 CNN layer, 5 FC layers and drop outs (to avoid overfitting)
#     4. Without init - my car was wandering of the street.
#     5. Activation layer used is 'ELU' (https://arxiv.org/abs/1511.07289) 

def nv_model():

    model = Sequential()
    model.add(Lambda(lambda x: x/127.5 - 1., input_shape=(64, 64, 3), output_shape=(64, 64, 3)))
    model.add(Convolution2D(24, 5, 5, subsample=(2, 2), border_mode="valid", init='he_normal', name='Conv1'))
    model.add(ELU())
    model.add(Convolution2D(12, 5, 5, subsample=(2, 2), border_mode="valid", init='he_normal', name='Conv2'))
    model.add(ELU())
    model.add(Dropout(0.3))   
    model.add(Convolution2D(48, 5, 5, subsample=(2, 2), border_mode="valid", init='he_normal', name='Conv3'))
    model.add(ELU())
    model.add(Convolution2D(64, 3, 3, subsample=(1, 1), border_mode="valid", init='he_normal', name='Conv4'))
    model.add(Dropout(0.2))
    model.add(ELU())   
    model.add(Convolution2D(64, 3, 3, subsample=(1, 1), border_mode="valid", init='he_normal', name='Conv5'))
    model.add(Flatten())
    model.add(ELU())
    model.add(Dense(1164, init='he_normal'))
    model.add(ELU())
    model.add(Dense(100, init='he_normal'))
    model.add(ELU())
    model.add(Dense(50, init='he_normal'))
    model.add(ELU())
    model.add(Dense(10, init='he_normal'))
    model.add(ELU())
    model.add(Dropout(0.2))
    model.add(Dense(1, init='he_normal'))
    return model

model= nv_model()

# Compile model
# Learning rate used is 0.0001 with higher learning rate - car starts wandering.
# Model is trained to minimize mse (mean-squared error) output of steerring angle
model.compile(optimizer=Adam(lr=0.0001), loss='mse')
                                                                                          
# Number of epochs and batch size
nb_epoch=10
batch_size = 256

# Get length of training and testing images
# Note: samples_per_epoch should be a number that can be divided by batch_size
nb_training = len(images_training)
nb_training = int(nb_training/256)*256
nb_validation = len(images_validation)
nb_validation= int(nb_validation/256)*256
                                                                                                                                                                                                                                                                                                                                                          
# Define checkpoint and early stop:
# Ref: https://keras.io/callbacks/#modelcheckpoint
# Used simple checkpoint strategy: to save the model weights to the same file, 
# if and only if the  validation accuracy improves.
# Arguments:
# monitor: quantity to be monitored (validation loss).
# min_delta: minimum change in the monitored quantity to qualify as an improvement
# patience: number of epochs with no improvement after which training will be stopped.

checkpoint = ModelCheckpoint('model.h5', monitor='val_loss', verbose=1, save_best_only=True)
early_stop = EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=3, verbose=1)

# Recording loss history
# Ref: https://keras.io/callbacks/#example-recording-loss-history
class lossHistory(keras.callbacks.Callback):
    def on_train_begin(self, logs={}):
        self.losses = []

    def on_batch_end(self, batch, logs={}):
        self.losses.append(logs.get('loss'))
        
losshistory = lossHistory()
                                                                                          
callbacks = [early_stop, checkpoint,losshistory] 
                                                                                          
#Start training
history=model.fit_generator(data_generator(images_training, angles_training, batch_size=batch_size),nb_training, nb_epoch,validation_data=data_generator(images_validation, angles_validation, batch_size=batch_size),callbacks=callbacks, nb_val_samples=nb_validation)                                                                                          

#Save the model in .json format
with open("model.json", "w") as json_file:
    json_file.write(model.to_json())
                                                                                          
########### END ################
                                                                                          
########### Visualizations ################ 
                                                                                          
                                                                                                                                                                                    
# Get stats of the input
#df.describe()

# Print a sample image and its angle (check how sky and hood of the car is shown, these are not needed for our analysis)
# print (images_training[6330])
# print (angles_training[6330])

# path = images_training[6330]
# path = path.replace(' ', '') # Remove extra space
# img = imread(path)
# plt.imshow(img)

# #Plot a graph of steering angle vs images - we can see that our test data is very biased to driving straight
# plt.hist(angles_training)
# plt.xlabel('Angle')
# plt.ylabel('Number of images')
# plt.show()
                                                                                          
#print summary of model
#model.summary() 
                                                                                          
# Visualize output of conv layer                                                                                          
# from keras.models import Sequential, Model

# img_path = "IMG/center_2016_12_01_13_32_43_457.jpg"

# def visualize(layer):
#     model2 = Model(input=model.input, output=model.get_layer(layer).output)

#     img = load_img(img_path)
#     img = crop_resize_image(img_to_array(img))
#     img = np.expand_dims(img, axis=0) #if dont do this then you will get this error: 
#     # expected lambda_input_8 to have 4 dimensions, but got array with shape (64, 64, 3)
#     print (img.shape)
#     features = model2.predict(img)
#     print("Shape: ", features.shape)
#     print (features[0])
#     # plot features
#     plt.subplots(figsize=(5, 5))
#     for i in range(16):
#         plt.subplot(4, 4, i+1)
#         plt.axis('off')
#         plt.imshow(features[0,:,:,i], cmap='gray') # note this 
#     plt.show()
                                                                                          
# visualize('Conv1')
# visualize('Conv2') 
# visualize('Conv3') 
                                                                                          


