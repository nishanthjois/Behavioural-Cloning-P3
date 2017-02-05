# Project 3: Behavioural Cloning 

## Description (Code/function wise description of the project):

### 1. Training data

  	1. Driving_log file contains left, right annd center image paths for every steering angle
  
    2. read_scv function reads driving_log file in pandas dataframe
  
    3. Image path and corresponding angles are read column wise
  
    4. As the training data has more left turns than right - additional data is generated by mirroring center images and adding a negative steering angle for the same (negative indicates right turn)
    
    5. Summary of training data:

![Alt text](/Sample-files/Describe.png?)
  
    6. Our training set is very biased to 0 - we need to fix this by image augmentation and generators (see below):

![Alt text](/Sample-files/Img_vs_angle.png?)

### 2. images_training, images_validation, angles_training, angles_validation = train_test_split(X, y, test_size=0.2,random_state=7)
    1. Data is split into trainig and validation data into 80:20 format (i.e., test size = 0.2)
    2. We are not spliting data for testing purpose as testing will be done on simulator

### 3. load_process_image
    1. Loads image from image path using imread
    2. Calls helper function augment_image and which returns augmented image and corresponding images
    3. Got better and faster results after reading reading Vivek's blog, before that I was using Keras generator and image augmention like this:
      train_datagen = ImageDataGenerator(
              rescale=1./255,
              shear_range=0.2,
              zoom_range=0.2,
              horizontal_flip=True)
      (More info in: https://chatbotslife.com/using-augmentation-to-mimic-human-driving-496b569760a9#.xh1deayrj)
        
### 4. height_width_augmentation
    1. Shift height and width by a small margin to simulate car being at different postions (left/right and up/down)
    2. After shifting we will add corresponding steering angles
 
### 5. brightness_augmentation
    1. Add random brightness to simulate car beging in different lighting conditions (sunlight, shadow, dawn/dusk, steertlight, etc.,)

### 6. Other augmention methods which I tried
    I haven't used in the project but I will try it out in future; adding here for reference:
      1. Channel shifting: It is the process of taking the red, green or blue values of pixels in an image and applying those values to pixels in different positions on the image
         From Keras documentation
        def random_channel_shift(x, intensity, channel_axis=0):
            x = np.rollaxis(x, channel_axis, 0)
            min_x, max_x = np.min(x), np.max(x)
            channel_images = [np.clip(x_channel + np.random.uniform(-intensity, intensity), min_x, max_x)
                            for x_channel in x]
            x = np.stack(channel_images, axis=0)
            x = np.rollaxis(x, 0, channel_axis + 1)
            return x
      
     2. Apply random shadow:
        More info: https://chatbotslife.com/using-augmentation-to-mimic-human-driving-496b569760a9#.xh1deayrj
       
     3. CV2 transformation examples:
        http://docs.opencv.org/3.1.0/da/d6e/tutorial_py_geometric_transformations.html
       
     4. As mentioned before Keras too provides lots of image augmention parameters
        from keras.preprocessing.image import ImageDataGenerator
        datagen = ImageDataGenerator(
          rotation_range=40,
          width_shift_range=0.2,
          height_shift_range=0.2,
          rescale=1./255,
          shear_range=0.2,
          zoom_range=0.2,
          horizontal_flip=True,
          fill_mode='nearest')
### 7. crop_resize_image
      Crop the image so that sky and car's hood is removed from the image - it both removes unwanted part of the image and also leads to less overhead in computation.

### Augmentaion results:

![Alt text](Sample-files/Augmentation.png?)
 
### 8. data_generator
    1. Generates batch of images and steering angles by using Python's yield
    2. Reason for using generator is to reduce memory overhead as we are dealing with more than 20K images

### 8. Nvidia model
    1. Nvidia model is used with input image size as 64*64
    2. First layer is normalization layer
    3. Model:
    
![Alt text](/Sample-files/model.png?)  

### 9. Other models
    1. I tried comma.ai model, but finally stuck with Nvidia model. No perticular reason to choose against comma.ai model - most of my testing was done on Nvidia model so I stuck to it. (Will try VGG or other models in free time)
    
### 10. Adam optimizer
    1. Learning rate is 0.0001 with higher learning rate - car starts wandering
    2. Note: adam to uses a larger effective step size, 
    and the algorithm will converge to this step size without fine tuning.
    
### 11. Epoch
    1. With just using Keras image generator (as mentioned in #3 and no separate data generator)- I had to used atleast 25 epochs to train the model correctly
    2. With using of data_generator and augmentation mentioned above it takes only 10 max.
    3. Final epoch:
    Epoch 10/10
    25344/25600 [============================>.] - ETA: 1s - loss: 0.0308Epoch 00009: val_loss improved from 0.02976 to     0.02777, saving model to model56.h5
    25600/25600 [==============================] - 128s - loss: 0.0309 - val_loss: 0.0278

### 12. Batch size and training/validation samples
    1. I used 128 too but 256 was faster and got same results. 
    2. I got warning to use correct samples_per_epoch and solved it by having samples_per_epoch a number that can be divided by batch_size: 
    nb_validation = len(images_validation)
    nb_validation== int(nb_validation/256)*256
### 13. Checkpoint, early stop and callbacks
    Ref: https://keras.io/callbacks/#earlystopping
    Code: 
    checkpoint = ModelCheckpoint('model56.h5', monitor='val_loss', verbose=1, save_best_only=True)
    early_stop = EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=3, verbose=1)
    
    1. Used simpler checkpoint strategy: to save the model weights to the same file, if and only if the  validation accuracy improves.
    2. Arguments:
    monitor: quantity to be monitored.
    min_delta: minimum change in the monitored quantity to qualify as an improvement
    patience: number of epochs with no improvement after which training will be stopped.
### 14. model.fit_generator
    1. Takes python generator as input of training data and validation data with callback strategy and trains the model for a     fixed number of epochs.

### 15. Save model
    1. Weights are saved in .h5 format and model in .json format - these along with drive.py will be used to run the simulator
    2. Code: 
    with open("model56.json", "w") as json_file:
          json_file.write(model.to_json())

### 16. Drive.py
    1. Edited this file to take cropped image size as input similar to my model.py (without this change my car was not moving at all even though model was displaying steering angles in terminal).
    2. Tried various throttle from 0.1 to 0.3 - 
      - 0.12 to 0.20 was most suitable for track #1 with steering angle default
      - 0.3 was sutiable for track #2 with steering angle mutlipled by 1.4; and image quality 'fastest' 

### 17. Training data
    1. I started with by training for 5-7 laps with keyboard and generated around 40k samples but after training with it I didn't get good results - car started wandering around near bridge and lake.
    2. After reading few blogs I thought I should try with joystick but had issues with joystick on my Ubuntu.
    3. Finally, few people in forum said that new data from Udacity is more than enough - I used it to train my model and it worked without issues.
      
### 18. Future work
    1. Make car run smooth
    2. Train with more models
    
Note: This project would not have been completed without forums and blogs which Udacity students have written, special thanks to everyone. 

