# Motion Detection

## Motivation
Current systems for motion activated cameras cost quite a large sum, and thus I thought it would be an interesting project to see how cheap I can get a motion activated camera to be using an ESP32 microcontroller connected to a camera communicating to a central hub. 

## Method
Similar to my volleyball project [here](https://matthew-bird.com/blogs/Body-World-Eye-Mapping.html), I take the median of the past n frames to create an estimate of what the background should look like with no moving object in it. Then, I take the difference between the current image and the background, and if the proportion of pixels with a difference above a threshold is above a threshold, motion is detected and a video is saved. 

To make the script capable of running in real time with multiple cameras, I also chose to resize the image to 192 x 108 for the median calculations, as that was originally accounting for 95% of the total processing time. 

The script saves all the scenes of the input video where movement is detected as a series of videos in an output directory. 

### Images (taken from the Volleyball project)
<ins>Input</ins>

<img width="300" alt="" src="https://github.com/user-attachments/assets/7e0de23f-ec21-415d-99fb-8aeeec2cbe24">

<ins>Median</ins>

<img width="300" alt="" src="https://github.com/user-attachments/assets/a69cbb11-b2bc-475b-ac3b-73f1d2eea2bc">

<ins>Movement mask</ins>

<img width="300" alt="" src="https://github.com/user-attachments/assets/46401ff6-493c-44b8-ac2b-f0ea40fb09fd">

## Setup
1. Upload .mp4 files to the In directory
2. Run example.ipynb
