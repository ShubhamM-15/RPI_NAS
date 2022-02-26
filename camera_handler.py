import numpy as np

from storage_handler import StorageHandler
import cv2
import logging
import time
logger = logging.getLogger(__name__)

class CameraHandler:
    def __init__(self, captureStream, config, debug=False):
        self.stream = captureStream
        self.config = config
        self.resolution = tuple(config['resolution_wh'])
        self.resize = False
        self.fps = config['fps']
        self.captureWait = 1/self.fps
        self.debug = debug

        self.maxMisses = 20
        self.storage = None
        # TODO Implement L13 LED for status on RPI

    def __setupCam(self, cam):
        cam.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

    def begin(self):
        # This is major camera loop that captures and saves
        logger.info("Initiating camera open")
        # TODO How to get audio too ??
        cam = cv2.VideoCapture(self.stream)
        if cam is None or not cam.isOpened():
            logger.fatal(f"Unable to open camera at {self.stream}")
            return -1
        logger.info(f"Camera opened at {self.stream} running application")
        self.__setupCam(cam)

        # Prepare framebuffer
        ret, fetchFrame = cam.read()
        if ret:
            if self.resolution[0] == -1 and self.resolution[1] == -1:
                self.resize = False
                self.resolution = fetchFrame.shape[:2][::-1]
            else:
                self.resize = True
                fetchFrame = cv2.resize(fetchFrame, dsize=self.resolution)
            self.storage = StorageHandler(self.config, fetchFrame)
            if not self.storage.isReady:
                logger.fatal("Storage Handler initialization failed: Unable to access storage directory.")
                return False
            logger.info(f"Camera Read Successful. Setup Done with resolution: {self.resolution}")
        else:
            logger.error("Unable to capture frame from camera. exiting")
            return -1

        logger.info("Running loop for grab retrieve and dump...")
        errorCount = 0
        while True:
            #t0 = time.time()
            try:
                stime = time.time()
                ret, fetchFrame = cam.read()
                if self.resize:
                    fetchFrame = cv2.resize(fetchFrame, dsize=self.resolution)
                if ret:
                    errorCount = 0
                    self.storage.updateFrame(fetchFrame)
                    if self.debug:
                        cv2.imshow("Frames", fetchFrame)
                        cv2.waitKey(1)
                    time.sleep(max(0.001, self.captureWait - (time.time()-stime)))
                else:
                    errorCount += 1
                    logger.error("Camera closed while application was running")
            except Exception as e:
                errorCount += 1
                logger.error(f"Capturing failed: {e}")
            if errorCount > self.maxMisses:
                logger.fatal("Max Misses surpassed. exiting application")
                cv2.destroyAllWindows()
                self.storage.forceDump()
                return -1
            #print(f'update time: {time.time() - t0} s')