import logging
import cv2
import os
import numpy as np
import time
from datetime import datetime
import shutil
from utils.frame_queue import Queue
from concurrent.futures import ThreadPoolExecutor
import gc

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
        self.maxMisses = 20
        self.clipStartTime = time.time()
        self.frameShape = frame.shape[:2][::-1]
        self.frameCH = frame.shape[2]
        self.frameSize = frame.nbytes / (1024*1024)
        self.forceExport = False
        self.cvExport = None
        self.videoPath = ""

        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix='export_handler')
        self.q = Queue(maxsize=5)

        os.makedirs(self.storePath, exist_ok=True)
        self.isReady = self.__checkStorage()
        self.isReady = self.isReady and self.__prepareStoreMetaData()
        if self.isReady:
            self.executor.submit(self.__exportHandler)
            logger.info("Storage Handler launched and ready")
        else:
            logger.error("Storage Handler failed to initialize")

    def __exportHandler(self):
        # This is a never ending Daemon worker
        logger.info("export_handler: executor thread export_handler")
        if self.cvExport is None:
            self.frameCounter = 0
            self.clipStartTime = time.time()
            dname, fname = self.__getFileName()
            os.makedirs(os.path.join(self.storePath, dname), exist_ok=True)
            self.videoPath = os.path.join(self.storePath, dname, fname)
            self.cvExport = cv2.VideoWriter(self.videoPath, cv2.VideoWriter_fourcc(*'MP4V'),
                                            self.fps, self.frameShape)
            # Update meta data
            if dname not in self.storeMetaData.keys():
                self.storeMetaData[dname] = []
            self.storeMetaData[dname].append(fname)

        errorCount = 0
        while True:
            frame = self.q.dequeue(block=True, timeout=2)
            if frame is not None:
                errorCount = 0
                if self.forceExport:
                    logger.info("export_handler: export_handler forced to dump")
                    self.cvExport.write(frame)
                    self.cvExport.release()
                    logger.info(f"export_handler: video: {self.videoPath} saved successfully")
                    logger.info("export_handler: forced-dump done, terminating thread.")
                    self.forceExport = False
                    return True
                else:
                    cspan = time.time() - self.clipStartTime
                    if cspan >= self.exportDuration:
                        self.executor.submit(self.__handleStorage)
                        logger.info(f"export_handler: Executing save video with {self.frameCounter} frames at {self.fps} fps")
                        self.fps = self.frameCounter / cspan
                        self.cvExport.write(frame)
                        self.cvExport.release()
                        logger.info(f"export_handler: video: {self.videoPath} saved successfully")
                        self.frameCounter = 0
                        self.clipStartTime = time.time()
                        dname, fname = self.__getFileName()
                        self.videoPath = os.path.join(self.storePath, dname, fname)
                        self.cvExport = cv2.VideoWriter(self.videoPath, cv2.VideoWriter_fourcc(*'MP4V'),
                                                        self.fps, self.frameShape)
                        # Update meta data
                        if dname not in self.storeMetaData.keys():
                            self.storeMetaData[dname] = []
                        self.storeMetaData[dname].append(fname)
                    else:
                        self.cvExport.write(frame)
                        self.frameCounter += 1
                del frame
                gc.collect()
            else:
                logger.info("export_handler: dequeue frame timed out")
                errorCount += 1
            if errorCount >= self.maxMisses:
                logger.fatal("Max error count surpassed in camera handler. Exiting.")
                return False

    def __checkStorage(self):
        t = np.zeros(self.frameShape, dtype=np.uint8)
        np.save(os.path.join(self.storePath, 'test.npy'), t)
        if os.path.isfile(os.path.join(self.storePath, 'test.npy')):
            os.remove(os.path.join(self.storePath, 'test.npy'))
            return True
        else:
            return False

    def __getFileName(self):
        fName = datetime.today().strftime('%H_%M_%S')
        dName = datetime.today().strftime('%d_%m_%y')
        fName = fName + self.videoFormat
        return dName, fName

    def __prepareStoreMetaData(self):
        # list date folders
        try:
            dates = []
            for it in os.scandir(self.storePath):
                if it.is_dir():
                    date = os.path.split(it.path)[-1]
                    if date != 'dump':
                        dates.append(date)
            dates.sort(key=lambda date: datetime.strptime(date, '%d_%m_%y'))
            for date in dates:
                self.storeMetaData[date] = []

            # list time files
            for date in self.storeMetaData.keys():
                files = []
                for it in os.scandir(os.path.join(self.storePath, date)):
                    if it.is_file():
                        files.append(os.path.split(it.path)[-1])
                #files.sort(key=lambda file: datetime.strptime(file.split('.')[0], '%H_%M_%S'))
                self.storeMetaData[date] = files
            logger.info("Storage mapped successfully")
            return True
        except:
            logger.error("Error in mapping data storage. Please format.")
            return False

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

    def __handleStorage(self):
        used = self.__findStoreSize()
        while used >= self.maxStorage + (self.frameSize * self.frameCounter * 2):
            # delete last day data
            dates = list(self.storeMetaData.keys())
            dates.sort(key=lambda date: datetime.strptime(date, '%d_%m_%y'))
            delDate = dates[0]
            shutil.rmtree(os.path.join(self.storePath, delDate))
            self.storeMetaData.pop(delDate, None)
            used = self.__findStoreSize()
            logger.info(f"Deleted folder: {os.path.join(self.storePath, delDate)}")

    def updateFrame(self, frame: np.ndarray):
        enqStat = self.q.enqueue(frame, block=True, timeout=2)
        if not enqStat:
            logger.error("Unable to enqueue frame for exporting, timed out")
            return False
        return True

    def forceDump(self):
        logger.info("Force dump initiated")
        self.forceExport = True
        self.frameCounter = 0
        self.clipStartTime = time.time()
        self.executor.shutdown(wait=True)
        logging.info("All standing exports done. Exiting storage handler.")
