import PySimpleGUI as sg


class wxAutomator:
    def __init__(self, sg):
        self.app = sg

    def send_pyq(self, serialno,deviceName):
        self.app.add_log(f"{deviceName}:开始发送朋友圈")
        pass
