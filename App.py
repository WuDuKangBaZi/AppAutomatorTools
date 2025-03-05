import datetime
import threading
import time
import PySimpleGUI as sg
import adbutils as adb
import requests
from setuptools.command.build_ext import if_dl
from urllib3.exceptions import MaxRetryError

from script.wxAutomator import wxAutomator
from util.deviceUtil import deviceUtil
from util.sqliteUtil import dbUtil


class AppAutomatorTools:
    def __init__(self, version="0.0.1"):
        self.appTask = []
        self.support_task = []
        self.script_list = {}
        self.thread = None
        self.version = version
        self.data = []
        self.appList = []
        self.supportApp = []
        self.db = dbUtil()
        self.deviceUtil = deviceUtil()
        self.wxAutomator = wxAutomator(self)
        self.window = None
        self.init_gui()
        self.device_info = []
        self.device_his = []
        self.task_threads = []

    def init_gui(self):
        """初始化GUI"""
        menu_def = [
            ["&帮助", ["&关于", "&赞赏"]]
        ]
        device_table = [
            [sg.Table(
                values=[[]],
                headings=["设备ID", "状态", "别名"],
                auto_size_columns=True,
                justification="center",
                key="-DEVICE-TABLE-",
                enable_events=True,
                expand_x=True,
                expand_y=True,
                enable_click_events=True,
                right_click_menu=["&右键菜单", ['更改别名::row_info', '查看记录::row_info', "选择运行::row_info"]]
            )]
        ]
        settings_table = [
            [sg.Text("AppKey:"), sg.InputText(key="-AppKey-"), sg.Button("保存Key")],
            [sg.Text("服务器地址："), sg.InputText(key="-server_host-"), sg.Button("保存服务器地址")]
        ]
        log_layout = [
            [sg.Multiline(key="-LOG-", disabled=True, expand_y=True, expand_x=True, autoscroll=True,
                          right_click_menu=["&右键菜单", ['清空日志']])]
        ]

        query_his = [
            [sg.Table(
                values=[[]],
                headings=["设备ID", "执行脚本", "发送时间"],
                auto_size_columns=True,
                justification="center",
                key="-HIS-TABLE-",
                expand_x=True,
                expand_y=True,
                enable_click_events=False,

            )]
        ]
        home_layout = [
            [sg.Button("刷新", key='-refacescript-')],
            [sg.Table(
                values=[[]],
                headings=["App名称", "支持版本", "脚本数量"],
                auto_size_columns=True,
                justification="center",
                key="-appList-",
                expand_x=True,
                expand_y=True,
                enable_click_events=False
            )]
        ]
        layout = [[sg.Menu(menu_def)],
                  [sg.TabGroup(

                      [
                          [sg.Tab("首页", home_layout)],
                          [sg.Tab("设备列表", device_table, key="-deviceList-")],
                          [sg.Tab("历史记录", query_his, key="query_his")],
                          [sg.Tab("设置", settings_table)],
                          [sg.Tab("日志记录", log_layout)]],

                      expand_x=True, expand_y=True, key="-TABGROUP-")]
            , [sg.StatusBar("就绪", key="-STATUS-", size=200)]]

        self.window = sg.Window("安卓脚本运行管理器", layout, finalize=True, resizable=False, size=(800, 600))

    def clear_log(self):
        self.window['-LOG-'].update("")

    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_message = f"{timestamp} {message}\n"
        self.window['-LOG-'].update(log_message, append=True)

    def start_monitor(self):
        self.thread = threading.Thread(target=self.monitor_task, daemon=True)
        self.thread.start()
        threading.Thread(target=self.getAppList, daemon=True).start()

    def task_window(self):
        """
        脚本运行窗口
        :return:
        """
        task_layout = [
            [sg.Text("选择要运行的脚本"), sg.Combo(["本地", "在线"], key="scriptLocal", size=15, default_value="在线"),
             sg.Button("获取脚本")],
            [sg.Text("App名称:"),
             sg.Combo(self.supportApp, size=(40, 1), key='-supportapp-', readonly=True, enable_events=True)],
            [sg.Text("脚本功能:"),
             sg.Combo(self.appTask, size=(40, 1), key="-supporttask", readonly=True, enable_events=True)],
            [sg.Button("运行环境检查"), sg.Button("运行环境初始化")],
            [sg.Button("提交运行"), sg.Button("取消")]
        ]
        return sg.Window("脚本运行器", task_layout, modal=True)

    def monitor_task(self):
        """
        任务监控
        :return:
        """
        db = dbUtil()
        device_his = []
        db.update("update devices set status=?", ["离线"])
        while True:
            # 监控设备变更
            device_onile = []
            for item in adb.adb.device_list():
                if item.info['state'] == 'device':
                    serialno = item.info['serialno']
                    device_onile.append(serialno)
                    if serialno in device_his:
                        continue
                    device_his.append(serialno)
                    res = db.query("select * from devices where serialno=?", [serialno, ])
                    if not res:
                        db.insert_device(serialno, "在线", "undefined")
                        self.add_log(f"设备:{serialno}上线了")
                    else:
                        db.update("update devices set status=? where serialno=?", ["在线", serialno])
                        query_all = db.query("select name from devices where serialno = ?", [serialno])
                        self.add_log(f"设备:{query_all[0][0]} 上线了")
            result = list(set(device_his) - set(device_onile))
            for item in result:
                db.update("update devices set status = ? where serialno = ?", ["离线", item])
                query_all = db.query("select name from devices where serialno = ?", [item])
                self.add_log(f"设备:{query_all[0][0]} 离线了")
            device_his = device_onile
            # adb.adb.server_kill()
            self.data = db.query("select serialno,status,name from devices", [])
            self.window.write_event_value("monitor_task", self.data)
            time.sleep(5)  # 等待五秒后重新运行
            break

    def db_init(self):
        query_res = self.db.query("select value from settings where key = 'AppKey'", [])
        self.window['-AppKey-'].update(query_res[0][0])
        host_res = self.db.query("select value from settings where key='ServerHost'", [])
        self.window['-server_host-'].update(host_res[0][0])

    def device_init(self):
        self.data = self.db.query("select serialno,status,name from devices", [])
        self.window.write_event_value("monitor_task", self.data)

    def getAppList(self):
        self.appList.clear()
        try:
            self.window['-refacescript-'].update(disabled=True)
            res = requests.get(f"{self.window['-server_host-'].get()}/script/listApp")
            for item in res.json():
                self.appList.append([item['appName'], item['versionConcat'], item['scriptCount']])
            self.window.write_event_value("-UPDATE-APP-LIST-", {"message": "", "data": self.appList})
            self.add_log(f"在服务器{self.window['-server_host-'].get()}更新脚本列表完成。")
        except (MaxRetryError, requests.exceptions.ConnectionError):
            self.window.write_event_value("-UPDATE-APP-LIST-",
                                          {"message": "连接到脚本服务器失败", "data": self.appList})
            self.add_log("连接到在线脚本服务器失败，请联系服务器供应商")
        except:
            self.window.write_event_value("-UPDATE-APP-LIST-",
                                          {"message": "更新脚本列表时发生未知意外", "data": self.appList})
            self.add_log("连接到在线脚本服务器时发生未知意外，请联系作者")
        finally:
            self.window['-refacescript-'].update(disabled=False)

    def get_script_in_online(self):
        """
        从在线配置服务器获取脚本信息
        :return:
        """
        res = requests.get(f"{self.window['-server_host-'].get()}/script/list")
        self.supportApp.clear()
        self.script_list = res.json()
        print(self.script_list)
        for item in res.json():
            if item['appName'] in self.supportApp:
                continue
            else:
                self.supportApp.append(item['appName'])

    def run(self):
        self.window['-DEVICE-TABLE-'].update(values=self.data)
        self.db_init()
        self.start_monitor()
        while True:
            event, values = self.window.read()
            if event in (sg.WIN_CLOSED, "Exit"):
                break
            elif event == "关于":
                sg.popup("Info",
                         "APP Automator Tools \n Version 0.0.1 \n Created by Felix Yu \n Email : 2625821125@qq.com")
            elif event == "monitor_task":
                self.data = values[event]
                self.window['-DEVICE-TABLE-'].update(values=self.data)
            elif event == "更改别名::row_info":
                try:
                    selected_row_index = values['-DEVICE-TABLE-'][0]
                    if selected_row_index is not None:
                        table_data = self.window['-DEVICE-TABLE-'].get()
                        row_data = table_data[selected_row_index]
                        user_input = sg.popup_get_text(f"修改设备别名{row_data[0]}", f"别名修改:{row_data[0]}",
                                                       default_text=row_data[2])
                        if user_input is not None and user_input.strip() != "":
                            self.db.update("update devices set name = ? where serialno = ?", [user_input, row_data[0]])
                            self.window['-STATUS-'].update("别名修改成功")
                            self.device_init()

                except IndexError:
                    self.window['-STATUS-'].update("请选择一行")
            elif event == "查看记录::row_info":
                try:
                    selected_row_index = values['-DEVICE-TABLE-'][0]
                    if selected_row_index is not None:
                        table_data = self.window['-DEVICE-TABLE-'].get()
                        row_data = table_data[selected_row_index]
                        self.device_his = self.db.query("""
                        select case when  d.name != 'undefined' then d.name else d.serialno end,r.sendWord,r.sendTime from records r 
                        left join devices d on 
                        r.serialno = d.serialno where r.serialno = ?""", [row_data[0], ])
                        self.window['-HIS-TABLE-'].update(values=self.device_his)
                        self.window['-TABGROUP-'].Widget.select(2)
                except IndexError:
                    self.window['-STATUS-'].update("请选择一行")
            elif event == "选择运行::row_info":
                try:
                    selected_row_index = values['-DEVICE-TABLE-'][0]
                    if selected_row_index is not None:
                        table_data = self.window['-DEVICE-TABLE-'].get()
                        row_data = table_data[selected_row_index]
                        if row_data[1] != "在线":
                            sg.popup("错误",
                                     "当前选择的设备不在线或不空闲!不可运行脚本")
                        else:
                            task_window = self.task_window()
                            # 弹出窗口初始化
                            while True:
                                task_event, task_value = task_window.read()
                                if task_event == "获取脚本":
                                    if task_window['scriptLocal'].get() == "在线":
                                        self.get_script_in_online()
                                        task_window['-supportapp-'].update(values=self.supportApp)
                                    else:
                                        pass
                                if task_event == "-supportapp-":
                                    app_name = task_window['-supportapp-'].get()
                                    # 检查app环境
                                    package_name = list(set([item['appPackage'] for item in self.script_list if
                                                             item['appName'] == app_name]))
                                    if self.deviceUtil.checkPackage(row_data[0], package_name[0]):
                                        function_list = list(set([item['scriptName'] for item in self.script_list if
                                                                  item['appName'] == app_name]))
                                        print(function_list)
                                        task_window['-supporttask'].update(values=function_list)
                                    else:
                                        sg.popup("App未安装", "请安装App!")
                                    pass
                                if task_event in (sg.WIN_CLOSED, "取消"):
                                    break
                                if task_event == "-supporttask":
                                    package_name = list(set([item['appPackage'] for item in self.script_list if
                                                             item['appName'] == task_window['-supportapp-'].get()]))
                                    version_code = list(set([item["appVersion"] for item in self.script_list if
                                                             (item['appName'] == task_window['-supportapp-'].get()) and
                                                             (item['scriptName'] == task_window['-supporttask'].get())
                                                             ]))
                                    print(version_code)
                                    support_d = self.deviceUtil.check_package_version(row_data[0], package_name,
                                                                                      version_code)
                                    if not support_d:
                                        pass

                                if task_event == "运行环境检查":
                                    # 环境检查功能
                                    self.deviceUtil.check_package_version()
                                if task_event == "运行环境初始化":
                                    pass
                                if task_event == "提交运行":
                                    pass
                                else:
                                    print(task_event)
                                task_window.close()

                except IndexError:
                    self.window['-STATUS-'].update("请选择一行")
            elif event == "保存Key":
                app_key = self.window['-AppKey-'].get()
                self.db.update("update settings set value = ? where key = 'AppKey'", [app_key, ])
                self.window['-STATUS-'].update("保存Key成功")
            elif event == "add-log":
                self.add_log(values.get("log_message"))
            elif event == "清空日志":
                self.clear_log()
            elif event == "赞赏":
                pass
            elif event == "刷新":
                if self.window["-server_host-"].get() == "":
                    sg.popup("未配置服务器地址!")
                    self.window['-STATUS-'].update("未配置服务器地址")
                else:
                    self.window['-STATUS-'].update("正在获取服务器中的配置")
                    threading.Thread(target=self.getAppList, daemon=True).start()
            elif event == "-UPDATE-APP-LIST-":
                if values[event]:
                    if values[event]['message'] != "":
                        self.window['-STATUS-'].update(values[event]['message'])
                    else:
                        self.window['-appList-'].update(values=self.appList)
                        self.window['-STATUS-'].update("服务器配置获取完成")
            else:
                print(event)


if __name__ == "__main__":
    app = AppAutomatorTools(version="0.0.1")
    app.run()
