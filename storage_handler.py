import logging
import cv2
import os
import numpy as np
import time
from datetime import datetime
import shutil
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class StorageHandler:
    def __init__(self, config, frame: np.ndarray):
        logger.info("Initializing Storage Handler")
        self.storePath = config['save_dir']
        self.dumpDir = os.path.join(self.storePath, 'dump')
        self.maxStorage = int(config['max_storage_gb']) * 1024
        self.videoFormat = config['save_format']
        self.exportDuration = int(config['clip_duration_minutes']) * 60
        self.fps = config['fps']
        self.storeMetaData = {}
        self.frameCounter = 0
        self.clipStartTime = time.time()
        self.clipParts = []
        self.frameShape = frame.shape[:2][::-1]
        self.frameCH = frame.shape[2]
        self.frameSize = frame.nbytes / (1024*1024)
        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix='storage')

        os.makedirs(self.storePath, exist_ok=True)
        os.makedirs(self.dumpDir, exist_ok=True)
        shutil.rmtree(self.dumpDir)
        os.makedirs(self.dumpDir, exist_ok=True)
        self.__prepareStoreMetaData()
        self.isReady = self.__checkStorage()
        logger.info("Storage Handler Ready")

    def __checkStorage(self):
        t = np.zeros(self.frameShape, dtype=np.uint8)
        np.save(os.path.join(self.dumpDir, 'test.npy'), t)
        if os.path.isfile(os.path.join(self.dumpDir, 'test.npy')):
            return True
        else:
            return False

    def __getFileName(self):
        fName = datetime.today().strftime('%H_%M_%S')
        dName = datetime.today().strftime('%d_%m_%y')
        return dName, fName

    def __prepareStoreMetaData(self):
        # list date folders
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

    def __exportVideo(self, clipList, forced=False):
        dname, fname = self.__getFileName()
        if forced:
            fname = fname + "_forced" + self.videoFormat
        else:
            fname = fname + self.videoFormat
        try:
            # Check for free storage and clear if necessary
            used = self.__findStoreSize()
            while used >= self.maxStorage + (self.frameSize*len(clipList)*2):
                # delete last day data
                dates = list(self.storeMetaData.keys())
                delDate = dates[0]
                shutil.rmtree(os.path.join(self.storePath, delDate))
                self.storeMetaData.pop(delDate, None)
                used = self.__findStoreSize()
                logger.info(f"Deleted folder: {os.path.join(self.storePath, delDate)}")

            # Export Video
            os.makedirs(os.path.join(self.storePath, dname), exist_ok=True)
            writer = cv2.VideoWriter(os.path.join(self.storePath, dname, fname), cv2.VideoWriter_fourcc(*'MJPG'),
                                     self.fps, self.frameShape)
            for clip in clipList:
                path = os.path.join(self.dumpDir, clip)
                frame = np.load(path)
                writer.write(frame)
                os.remove(path)
            writer.release()
            logger.info(f"saved video: {os.path.join(self.storePath, dname, fname)}")
        except:
            logger.error("Export video failed. clearing dumped files")
            for clip in clipList:
                path = os.path.join(self.dumpDir, clip)
                os.remove(path)
        finally:
            # Update meta data
            if dname not in self.storeMetaData.keys():
                self.storeMetaData[dname] = []
            self.storeMetaData[dname].append(fname)

    def updateFrame(self, frame):
        # TODO optimize by keeping a buffer
        cspan = time.time() - self.clipStartTime
        if cspan >= self.exportDuration:
            self.fps = self.frameCounter/cspan
            logger.info(f"Executing save video with {len(self.clipParts)} frames at {self.fps} fps")
            self.executor.submit(self.__exportVideo, self.clipParts.copy())
            self.frameCounter = 0
            self.clipStartTime = time.time()
            self.clipParts.clear()
        tpath = datetime.today().strftime('%H_%M_%S.%f') + '.npy'
        np.save(os.path.join(self.dumpDir, tpath), frame)
        self.clipParts.append(tpath)
        self.frameCounter += 1

    def forceDump(self):
        logger.info("Force dump initiated")
        cspan = time.time() - self.clipStartTime
        self.fps = self.frameCounter / cspan
        self.executor.submit(self.__exportVideo, self.clipParts.copy(), True)
        self.frameCounter = 0
        self.clipStartTime = time.time()
        self.clipParts.clear()
