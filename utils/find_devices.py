import subprocess
import re
import os
import logging
logger = logging.getLogger(__name__)

class DeviceFinder:
    def __init__(self):
        pass

    def __listAllDevices(self, debug=False):
        if os.name in ['nt']:
            output = subprocess.check_output(['arp', '-a']).decode("utf-8")
        elif os.name in ['posix']:
            output = subprocess.check_output(['arp-scan', '--interface=wlan0', '--localnet']).decode("utf-8")
        else:
            logger.error("Unsupported System")
            return None
        entries = output.strip().split('\n')

        #Defining regex
        ipre = r'[0-9]+(?:\.[0-9]+){3}'
        macre = ("^([0-9A-Fa-f]{2}[:-])" + "{5}([0-9A-Fa-f]{2})|" + "([0-9a-fA-F]{4}\\."
                 + "[0-9a-fA-F]{4}\\." + "[0-9a-fA-F]{4})$")
        iprc = re.compile(ipre)
        macrc = re.compile(macre)

        dataList = []
        for entry in entries:
            entry = re.sub('[^a-zA-Z0-9\n\.:-]', ' ', entry)
            curip = None
            curmac = None
            values = entry.split(' ')
            for val in values:
                val = val.strip()
                mcfound = re.search(macrc, val)
                ipfound = re.search(iprc, val)
                if mcfound:
                    curmac = val
                if ipfound:
                    curip = val
            if curip is not None and curmac is not None:
                dataList.append([curip, curmac.replace('-', ':').upper()])

        if debug:
            for data in dataList:
                print(f"Found ip: {data[0]} with mac: {data[1].upper()}")
        return dataList

    def getIPofDevice(self, mac: str):
        ip = None
        allDevices = self.__listAllDevices()
        if allDevices is not None:
            for device in allDevices:
                if mac.upper() == device[1].upper():
                    ip = device[0].strip()
                    logger.info(f"Found ip {ip} for device {mac}")
                    break

        return ip

if __name__=="__main__":
    #mac = "20:A6:0C:90:AE:8E"
    mac = "B4:B0:24:AD:96:66"
    ipHandler = DeviceFinder()
    ip = ipHandler.getIPofDevice(mac)
    if ip is None:
        print(f"IP not found for {mac}")
    else:
        print(f"Found ip {ip} for mac {mac}")
