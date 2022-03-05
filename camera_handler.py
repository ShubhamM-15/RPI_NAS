import numpy as np
from concurrent.futures import ThreadPoolExecutor
from storage_handler import StorageHandler
import cv2
import logging
import time
from utils.frame_queue import Queue
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

        self.maxMisses = 20
        self.storage = None

        self.q = Queue(maxsize=5)
        self.cam = None
        self.camStatus = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='camera_daemon')
        # TODO Implement L13 LED for status on RPI

    def __frameCatchDaemon(self):
        logger.info("camera_daemon: Running loop for grab retrieve and dump...")
        errorCount = 0
        while True:
            try:
                ret, fetchFrame = self.cam.read()
                if self.resize:
                    cv2.resize(fetchFrame, dsize=self.resolution, dst=fetchFrame)
                if ret:
                    errorCount = 0
                    enqued = self.q.enqueue(fetchFrame, block=True, timeout=2)
                    if not enqued:
                        logger.error("camera_daemon: Unable to enqueue frame")
                else:
                    errorCount += 1
                    logger.error("camera_daemon: Camera closed while application was running")
            except Exception as e:
                errorCount += 1
                logger.error(f"camera_daemon: Capturing failed: {e}")
            if errorCount > self.maxMisses:
                logger.fatal("camera_daemon: Max Misses surpassed. exiting application")
                self.camStatus = False
                return False

    def __setupCam(self):
        self.cam.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

    def begin(self):
        # This is major camera loop that captures and saves
        logger.info("Initiating camera open")
        # TODO How to get audio too ??
        self.cam = cv2.VideoCapture(self.stream)
        if self.cam is None or not self.cam.isOpened():
            logger.fatal(f"Unable to open camera at {self.stream}")
            return -1
        logger.info(f"Camera opened at {self.stream} running application")
        self.__setupCam()

        # Prepare framebuffer
        ret, fetchFrame = self.cam.read()
        if ret:
            self.chn = fetchFrame.shape[2]
            if self.resolution[0] == -1 and self.resolution[1] == -1:
                self.resize = False
                self.resolution = fetchFrame.shape[:2][::-1]
            else:
                self.resize = True
                cv2.resize(fetchFrame, dsize=self.resolution, dst=fetchFrame)
            self.storage = StorageHandler(self.config, fetchFrame)
            if not self.storage.isReady:
                logger.fatal("Storage Handler initialization failed: Unable to access storage directory.")
                return False
            logger.info(f"Camera Read Successful. Setup Done with resolution: {self.resolution}")
        else:
            logger.error("Unable to capture frame from camera. exiting")
            return -1

        # Launch camera daemon
        self.executor.submit(self.__frameCatchDaemon)
        self.camStatus = True

        while self.camStatus:

            fetchFrame = self.q.dequeue(block=True, timeout=2)
            if fetchFrame is None:
                logger.error("unable to dequeue frame from camera_daemon, timed out")
                continue
            if self.resize:
                cv2.resize(fetchFrame, dsize=self.resolution, dst=fetchFrame)
            stime = time.time()
            self.storage.updateFrame(fetchFrame)
            print(f'update time: {time.time() - stime} s')
            del fetchFrame
            gc.collect()

