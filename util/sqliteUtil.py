import sqlite3 as sql
from datetime import datetime


class dbUtil:
    conn = None
    cursor = None

    def __init__(self):
        self.conn = sql.connect("save.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
                    create table if not exists devices(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serialno TEXT,
                    name TEXT,
                    status TEXT
                    )
                """)
        self.cursor.execute("""
                    create table if not exists records(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serialno TEXT,
                    sendWord TEXT,
                    sendTime TEXT)
                    """)
        self.cursor.execute("""
            create table if not exists settings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT,
            value TEXT)
        """)
        settings_keys = ['AppKey',"ServerHost"]
        for key in settings_keys:
            self.cursor.execute("select * from settings where key = ?", (key,))
            if not self.cursor.fetchone():
                self.cursor.execute("insert into settings(key,value)values (?,'')", (key,))
        self.cursor.execute("update settings set value = 'http://localhost:9091' where key = 'ServerHost'",())
        self.conn.commit()

    def close_db(self):
        self.cursor.close()
        self.conn.close()

    def insert_device(self, serialno, name, status):
        self.cursor.execute("insert into devices(serialno, name, status) values (?, ?, ?)", [serialno, name, status])
        self.conn.commit()

    def insert_his(self, serialno, sendWord):
        self.cursor.execute("insert into records(serialno, sendWord, sendTime) values (?, ?, ?)",
                            [serialno, sendWord, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        self.conn.commit()

    def query(self, query_str, params=None):
        self.cursor.execute(query_str, params)
        return self.cursor.fetchall()

    def update(self, query_str, params=None):
        self.cursor.execute(query_str, params)
        self.conn.commit()

    def delete(self, query_str, params=None):
        self.cursor.execute(query_str, params)
        self.conn.commit()
