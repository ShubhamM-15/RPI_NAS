import logging
import cv2
import os
import numpy as np
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class StorageHandler:
    def __init__(self, config, frame: np.ndarray):
        logger.info("Initializing Storage Handler")
        self.storePath = config['save_dir']
        self.maxStorage = int(config['max_storage_gb']) * 1024
        self.videoFormat = config['save_format']
        self.exportDuration = int(config['clip_duration_minutes']) * 60
        self.fps = config['fps']
        self.storeMetaData = {}
        self.frameCounter = 0
        self.clipStartTime = time.time()
        self.nFrames = self.fps * self.exportDuration
        self.framesize = frame.shape[:2][::-1]

        # Allocation framebuffer
        self.isReady = True
        try:
            self.framebuffer = [np.zeros(frame.shape, dtype=np.uint8) for _ in range(self.nFrames)]
            self.buffersize = (frame.nbytes * self.nFrames)/(1024*1024)
        except:
            logger.error("Unable to allocate framebuffer. Reduce clip_duration_minutes")
            self.isReady = False

        os.makedirs(self.storePath, exist_ok=True)
        self.__prepareStoreMetaData()
        logger.info("Storage Handler Ready")

    def __getFileName(self):
        fstamp = datetime.today().strftime('%H_%M_%S')
        return fstamp + self.videoFormat

    def __getDirName(self):
        return datetime.today().strftime('%d_%m_%y')

    def __prepareStoreMetaData(self):
        # list date folders
        for it in os.scandir(self.storePath):
            if it.is_dir():
                self.storeMetaData[os.path.split(it.path)[-1]] = []
        # list time files
        for date in self.storeMetaData.keys():
            for it in os.scandir(os.path.join(self.storePath, date)):
                if it.is_file():
                    self.storeMetaData[date].append(os.path.split(it.path)[-1])

    def __findStoreSize(self):
        size = 0
        # get size
        for path, dirs, files in os.walk(self.storePath):
            for f in files:
                fp = os.path.join(path, f)
                size += os.path.getsize(fp)
        sizeMB = (size / 1024) / 1024
        logger.info(f"Total size of used storage: {sizeMB} MB")
        return sizeMB

    def __exportVideo(self):
        # Check for storage size and delete if necessary
        used = self.__findStoreSize()
        if used >= self.maxStorage + self.buffersize * 2:
            # delete last day data
            pass

        fName = self.__getFileName()
        dName = self.__getDirName()
        os.makedirs(os.path.join(self.storePath, dName), exist_ok=True)
        exportPath = os.path.join(self.storePath, dName, fName)
        logger.info(f"Attempting to export video: {exportPath}")

        fps = self.frameCounter/(time.time() - self.clipStartTime)
        vwriter = cv2.VideoWriter(exportPath, cv2.VideoWriter_fourcc(*'MJPG'), fps, self.framesize)
        if not vwriter.isOpened():
            logger.error("Unable to open file for writing video")
            return False

        for i in range(self.frameCounter):
            vwriter.write(self.framebuffer[i])

        vwriter.release()
        logger.info("Video Export successful")
        return True

    def updateFrame(self, frame):
        if time.time() - self.clipStartTime >= self.exportDuration or self.frameCounter >= self.nFrames:
            # Thread for saving
            self.clipStartTime = time.time()
        else:
            np.copyto(self.framebuffer[self.frameCounter], frame)
            self.frameCounter += 1

    def forceDump(self):
        pass
