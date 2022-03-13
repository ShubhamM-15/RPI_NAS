import numpy as np
from concurrent.futures import ThreadPoolExecutor
from storage_handler import StorageHandler
import cv2
import logging
import time
from queue import Queue
import gc
logger = logging.getLogger(__name__)

class CameraHandler:
    def __init__(self, captureStream, config, debug=False):
        self.stream = captureStream
        self.config = config
        self.resolution = tuple(config['resolution_wh'])
        self.chn = 3
        self.resize = False
        self.fps = config['fps']
        self.captureWait = 1/self.fps
        self.debug = debug

        self.maxMisses = 10
        self.storage = None
        self.cam = None

    def __setupCam(self):
        self.cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def begin(self):
        # This is major camera loop that captures and saves
        logger.info("Initiating camera open")
        # TODO How to get audio too ??
        self.cam = cv2.VideoCapture(self.stream)
        if self.cam is None or not self.cam.isOpened():
            logger.fatal(f"Unable to open camera at {self.stream}")
            return False
        logger.info(f"Camera opened at {self.stream} running application")
        self.__setupCam()

        # Prepare framebuffer
        ret, fetchFrame = self.cam.read()
        if ret:
            logger.info(f'Camera stream running at resolution: {fetchFrame.shape}')
            self.chn = fetchFrame.shape[2]
            if self.resolution[0] == -1 and self.resolution[1] == -1:
                self.resize = False
                self.resolution = fetchFrame.shape[:2][::-1]
            else:
                self.resize = True
                logger.info(f'Resizing Enabled')
                cv2.resize(fetchFrame, dsize=self.resolution, dst=fetchFrame)
            self.storage = StorageHandler(self.config, fetchFrame)
            if not self.storage.isReady:
                logger.fatal("Storage Handler initialization failed: Unable to access storage directory.")
                return False
            logger.info(f"Camera Read Successful. Setup Done with resolution: {self.resolution}")
        else:
            logger.error("Unable to capture frame from camera. exiting")
            return False

        errorCount = 0
        logger.info("Running camera loop ...")
        while True:
            ret, fetchFrame = self.cam.read()
            if ret:
                if self.resize:
                    cv2.resize(fetchFrame, dsize=self.resolution, dst=fetchFrame)
                updated = self.storage.updateFrame(fetchFrame)
                if updated:
                    errorCount = 0
                else:
                    errorCount += 1
                del fetchFrame
                gc.collect()
            else:
                errorCount += 1
                logger.error("Unable to fetch frame from camera")
            if errorCount >= self.maxMisses:
                logging.fatal("Camera loop: max error count surpassed. Breaking")
                break

        # Force dump
        self.storage.forceDump()

