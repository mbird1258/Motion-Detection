import numpy as np
import cv2
from matplotlib import pyplot as plt
import os

class VideoManager:
    def __init__(self, 
                 CameraStreams,
                 OutputDirectoryName=None,
                 MedianSize=60, 
                 MovementThreshold=30, 
                 MovementBlobSizeThreshold=0.005,
                 MedianUpdateDelay=1,#30*60*1000, <- this would need to use delta of medians, bc otherwise if an object is moved it'll constantly report movement
                 RecordIncidentVideos=False,
                 IncidentVideoLength=[2000,1000],
                 MaxVideoLength=10000):
        self.MedianSize = MedianSize
        self.MovementThreshold = MovementThreshold
        self.MovementBlobSizeThreshold = MovementBlobSizeThreshold # ratio of pixels above movement threshold before determining as moving object (0-1)
        self.MedianUpdateDelay = MedianUpdateDelay # milliseconds
        self.RecordIncidentVideos = RecordIncidentVideos
        self.IncidentVideoLength = IncidentVideoLength # milliseconds
        self.MaxVideoLength = MaxVideoLength

        self.cameras = [Camera(self, stream, ind) for ind, stream in enumerate(CameraStreams)]
        
        self.OutputDirectoryName = OutputDirectoryName if RecordIncidentVideos==True else None
        if RecordIncidentVideos:
            for i in range(len(self.cameras)):
                path = f"Out/{self.OutputDirectoryName}/Camera {i}/" if self.OutputDirectoryName != None else f"Out/Camera {i}/"
                if not os.path.exists(path): os.makedirs(path)

        self.log=log()
    
    def LogIncident(self, FrameMS, camera):
        if self.RecordIncidentVideos:
            camera.VideoUpdateTime = FrameMS + self.IncidentVideoLength[1]
        
        self.log(FrameMS, camera.index)

        # ==!== If anything else to do when incident occurs, put here ==!== #
        pass

        return
    
    def StoreVid(self, camera, path, video):
        NumFilesInPath = len([i for i in os.listdir(path) if os.path.isfile(os.path.join(path, i))])
        path += f"{NumFilesInPath}.mp4"

        height, width, _ = video[0].shape

        out = cv2.VideoWriter(path, 
                              cv2.VideoWriter_fourcc(*'mp4v'), 
                              camera.stream.get(cv2.CAP_PROP_FPS), 
                              (width,height))

        for img in video:
            out.write(img)

        out.release()
    
    def UpdateVideoAsync(self, FrameMS, CameraInd, force=False):
        camera = self.cameras[CameraInd]
        if not camera.VideoUpdateTime:
            return

        if force or FrameMS > camera.VideoUpdateTime or FrameMS > camera.VideoFirstUpdateTime + self.MaxVideoLength - self.IncidentVideoLength[0]:
            path = f"Out/{self.OutputDirectoryName}/Camera {CameraInd}/" if self.OutputDirectoryName != None else f"Out/Camera {CameraInd}/"
            self.StoreVid(camera, path, camera.IntrusionPlaybackVideo)
            camera.VideoUpdateTime = None

    def main(self):
        if len([i for i in self.cameras if i is not None]) == 0:
            return False, self.log

        str = ""
        for ind, camera in enumerate(self.cameras):
            FrameMS = camera.stream.get(cv2.CAP_PROP_POS_MSEC)
            str += f"{ind}: {np.round(FrameMS,2)/1000} || "

            img = camera.ReadImage(FrameMS)
            if type(img) != np.ndarray:
                continue

            camera.UpdateMedian(img, FrameMS)
            movement = camera.CheckForMovement(img)

            if movement:
                self.LogIncident(FrameMS, camera)
        print(str[:-4])

        return True, self.log


class Camera:
    '''
    Class that contains attribute of the camera, such as the camera stream or camera median(background)
    '''

    def __init__(self, manager, stream, index):
        self.VideoManager = manager
        self.stream = stream
        self.index = index

        self.LastMedianUpdateTime = -np.inf
        self.IntrusionPlaybackVideo = [] if self.VideoManager.RecordIncidentVideos else None
        self.VideoUpdateTime = None
        self.VideoFirstUpdateTime = None
        self.MedianImages = []
        self.median = None

    def ReadImage(self, FrameMS):
        res, img = self.stream.read()
        if not res:
            self.VideoManager.UpdateVideoAsync(FrameMS, self.index, force=True)
            
            print(f"Camera {self.index} no input, removing from VideoManager")
            self.VideoManager.cameras[self.index] = None

            return False
        
        if self.VideoManager.RecordIncidentVideos:
            self.VideoManager.UpdateVideoAsync(FrameMS, self.index)

            if self.VideoUpdateTime:
                self.IntrusionPlaybackVideo = self.IntrusionPlaybackVideo + [img]
            else:
                self.IntrusionPlaybackVideo = self.IntrusionPlaybackVideo[-(int((self.VideoManager.IncidentVideoLength[0]+self.VideoManager.IncidentVideoLength[1])*self.stream.get(cv2.CAP_PROP_FPS)/1000)-1):] + [img]
                self.VideoFirstUpdateTime = FrameMS
        return img

    def ResizeToMedian(self, img, width=192, height=108):
        return cv2.resize(img, (width, height))

    def UpdateMedian(self, img, FrameMS):
        if len(self.MedianImages) == self.VideoManager.MedianSize and FrameMS - self.LastMedianUpdateTime < self.VideoManager.MedianUpdateDelay:
            return

        self.LastMedianUpdateTime = FrameMS
        self.MedianImages = self.MedianImages[-(self.VideoManager.MedianSize-1):] + [self.ResizeToMedian(img)]
        self.median = np.median(self.MedianImages, axis=0).astype(np.uint8)
    
    def CheckForMovement(self, img):
        if np.count_nonzero(np.average(np.abs(self.ResizeToMedian(img).astype(np.int16) - self.median.astype(np.int16)), axis=2) >= self.VideoManager.MovementThreshold) > self.VideoManager.MovementBlobSizeThreshold * self.median[:, :, 0].size:
            return True
        
        return False


class log:
    def __init__(self):
        self.contents = []
    
    def __call__(self, FrameMS, CameraIndex):
        self.contents.append((FrameMS, CameraIndex))

    def __str__(self):
        if len(self.contents) == 0:
            return "No Contents"
        
        out = ""
        for ind, entry in enumerate(self.contents):
            out = out+f"\nIndex: {ind} || Time(s): {np.round(entry[0]/1000, 2)} || Camera Number: {entry[1]}"
        
        return out

'''
For each camera:
    Read image
    Update the median with image
    Check for any movement within image
    If movement, contact RFID checker
    If RFID detected in the direction of the movement, ignore movement -> if rfid present at all, no need to be concerned about intruder - rfid guy got it ^^ (I'm lazy af)
        Else, log/report/save video data
'''