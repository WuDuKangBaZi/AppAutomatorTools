import adbutils as adb

from util.sqliteUtil import dbUtil
import uiautomator2 as u


class deviceUtil:
    def __init__(self):
        self.db = dbUtil()

    def reloadDevice(self):
        print("reloadDevice")
        for item in adb.adb.device_list():
            print(item.info)
            if item.info['state'] == 'device':
                serialno = item.info['serialno']
                res = self.db.query("select * from devices where serialno=?", [serialno, ])
                if not res:
                    self.db.insert_device(serialno, "undefind", "online")

        return self.db.query("select * from devices", [])

    def checkPackage(self, serialno, packageName):
        print(serialno)
        d = u.connect(serialno)
        return d.app_list(packageName)

    def check_package_version(self,serialno,packageName,versionName):
        d = u.connect(serialno)
        app_info = d.app_info(packageName)
        if (app_info['versionName'] == versionName) or (app_info['versionCode'] == versionName):
            return True
        else:
            return False
