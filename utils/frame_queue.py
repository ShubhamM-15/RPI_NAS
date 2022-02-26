import time
class Queue:
    def __init__(self, maxsize=5, recheck_time=0.001):
        self.queue = []
        self.nElem = 0
        self.maxsize = maxsize
        self.rchk = recheck_time

    def enqueue(self, item, block=False, timeout=None):
        if block and timeout is not None:
            stime = time.time()
            while time.time() - stime <= timeout:
                if self.nElem < self.maxsize:
                    self.queue.append(item)
                    self.nElem += 1
                    return True
                time.sleep(self.rchk)
            return False
        if block and timeout is None:
            while True:
                if self.nElem < self.maxsize:
                    self.queue.append(item)
                    self.nElem += 1
                    return True
                time.sleep(self.rchk)
        if not block:
            if self.nElem < self.maxsize:
                self.queue.append(item)
                self.nElem += 1
                return True
            else:
                return False

    def dequeue(self, block=False, timeout=None):
        if block and timeout is not None:
            stime = time.time()
            while time.time() - stime <= timeout:
                if self.nElem > 1:
                    self.nElem -= 1
                    return self.queue.pop(0)
                time.sleep(self.rchk)
            return None
        if block and timeout is None:
            while True:
                if self.nElem > 1:
                    self.nElem -= 1
                    return self.queue.pop(0)
                time.sleep(self.rchk)
        if not block:
            if self.nElem > 1:
                self.nElem -= 1
                return self.queue.pop(0)
            else:
                return None

    def display(self):
        print(self.queue)

    def size(self):
        return self.nElem