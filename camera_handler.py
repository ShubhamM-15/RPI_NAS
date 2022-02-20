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
        workFrame = np.zeros((self.resolution[1], self.resolution[0], fetchFrame.shape[2]), dtype=np.uint8)
        if ret:
            if fetchFrame.shape[:2][::-1] != self.resolution:
                self.resize = True
                cv2.resize(fetchFrame, dsize=self.resolution, dst=workFrame)
            else:
                self.resize = False
                np.copyto(workFrame, fetchFrame)
            self.storage = StorageHandler(self.config, workFrame)
            if not self.storage.isReady:
                logger.fatal("Storage Handler initialization failed: Unable to access storage directory.")
                return False
            logger.info("Camera Read Successful. Setup Done.")
        else:
            logger.error("Unable to capture frame from camera. exiting")
            return -1

        logger.info("Running loop for grab retrieve and dump...")
        errorCount = 0
        while True:
            try:
                if cam.isOpened():
                    stime = time.time()
                    ret, _ = cam.read(image=fetchFrame)
                    if self.resize:
                        cv2.resize(fetchFrame, dsize=self.resolution, dst=workFrame)
                    else:
                        np.copyto(workFrame, fetchFrame)
                    if ret:
                        errorCount = 0
                        self.storage.updateFrame(workFrame)
                        if self.debug:
                            cv2.imshow("Frames", workFrame)
                            cv2.waitKey(1)
                        time.sleep(max(0.001, self.captureWait - (time.time()-stime)))
                    else:
                        errorCount += 1
                        logger.error("Camera closed while application was running")
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