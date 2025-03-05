import win32file
import win32event
import win32con
import threading

class DeviceMonitor(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.hDevice = win32file.CreateFile(
            "\\\\.\\PhysicalDrive0",
            win32con.GENERIC_READ,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL,
            None
        )
        self.hEvent = win32event.CreateEvent(None, False, False, None)
        self.running = True

    def run(self):
        while self.running:
            win32file.DeviceIoControl(
                self.hDevice,
                win32con.IOCTL_STORAGE_CHECK_VERIFY2,
                None,
                None,
                self.hEvent
            )
            rc = win32event.WaitForSingleObject(self.hEvent, 500)
            if rc == win32event.WAIT_OBJECT_0:
                print("Device change detected")

    def stop(self):
        self.running = False
        win32event.SetEvent(self.hEvent)
        self.join()

if __name__ == "__main__":
    monitor = DeviceMonitor()
    monitor.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        monitor.stop()