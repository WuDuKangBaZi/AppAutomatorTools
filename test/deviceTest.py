import adbutils
import uiautomator2 as u

d = u.connect()
print(d.app_list("tv.danmaku.bili"))
print(d.app_info("tv.danmaku.bili"))