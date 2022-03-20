import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from storage_handler import StorageHandler
import cv2
import logging
import gc
logger = logging.getLogger(__name__)


def setupCam(cam):
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

def frameCatchDaemon(stream, frameQueue, camStatus):
    logger = logging.getLogger(__name__)
    logger.info("CameraProcess: Camera Process Initiated")

    cam = cv2.VideoCapture(stream)
    if cam is None or not cam.isOpened():
        logger.fatal("CameraProcess: Unable to open camera stream. Exiting.")
        return False
    setupCam(cam)
    camStatus.set(True)
    logger.info("CameraProcess: Camera setup done. Running capture...")

    errorCount = 0
    while camStatus.get():
        try:
            ret, fetchFrame = cam.read()
            if ret:
                errorCount = 0
                try:
                    frameQueue.put(fetchFrame, block=False)
                except:
                    pass
            else:
                errorCount += 1
        except Exception as e:
            errorCount += 1
        if errorCount > 10:
            camStatus.set(False)
            logger.info("CameraProcess: Max errors surpassed. Exiting.")
            return False

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
        self.manager = multiprocessing.Manager()
        self.q = self.manager.Queue(maxsize=1)
        self.camStatus = self.manager.Value('i', False)
        self.executor = ProcessPoolExecutor(max_workers=1)

    def begin(self):
        # Test camera setup and validate
        logger.info("Initiating camera open")
        self.cam = cv2.VideoCapture(self.stream)
        if self.cam is None or not self.cam.isOpened():
            logger.fatal(f"Unable to open camera at {self.stream}")
            return False
        logger.info(f"Camera opened at {self.stream} running application")

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
            logger.info(f"Camera Read Successful. Setup Done with resolution: {self.resolution}")
        else:
            logger.error("Unable to capture frame from camera. exiting")
            return False
        self.cam.release()

        # Launch camera daemon
        self.executor.submit(frameCatchDaemon, self.stream, self.q, self.camStatus)
        logger.info("Waiting for camera thread to initiate")
        waitCycles=0
        while not self.camStatus.get():
            time.sleep(1)
            waitCycles += 1
            if waitCycles >= 10:
                logger.fatal("Camera Process not started yet!!")
                self.camStatus.set(False)
                self.executor.shutdown(wait=True)
                logger.error("Camera Process failed. Exiting application.")
                return False

        # Prepare storage handler
        self.storage = StorageHandler(self.config, fetchFrame)
        if not self.storage.isReady:
            logger.fatal("Storage Handler initialization failed: Unable to access storage directory.")
            return False

        # Run update loop in camera
        errorCount = 0
        while self.camStatus.get():
            try:
                fetchFrame = self.q.get(block=True, timeout=1)
            except:
                logger.error("unable to dequeue frame from camera_daemon, timed out")
                errorCount += 1
                fetchFrame = None
            if fetchFrame is not None:
                if self.resize:
                    cv2.resize(fetchFrame, dsize=self.resolution, dst=fetchFrame)
                updated = self.storage.updateFrame(fetchFrame)
                if updated:
                    errorCount = 0
                else:
                    errorCount += 1
                del fetchFrame
                gc.collect()
            if errorCount >= self.maxMisses:
                logging.fatal("Camera loop: max error count surpassed. Breaking")
                self.camStatus.set(False)
                break

        # Force dump
        self.storage.forceDump()
        self.executor.shutdown(wait=True)
        logger.error("Exiting camera handler")

