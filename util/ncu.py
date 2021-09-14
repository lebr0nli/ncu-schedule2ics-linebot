import pandas as pd
from datetime import datetime, timedelta
import re
from icalendar import Calendar, Event, Alarm
import requests
import configparser
import os


def no_dup(username):
    h = f'{username}_{os.urandom(16).hex()}'
    for x in os.scandir("schedule"):
        if x.name.startswith(username):
            h = x.name[:-4]
            return h
    return h


class NCUCalendar:
    def __init__(self, username, password, announce_time):
        self.username = username
        self.announce_time = announce_time
        config = configparser.ConfigParser()
        config.read('util/config.ini')
        user_info = {"account": username,
                     "passwd": password}
        self.start_time = config['start_time']
        self.start_time = {x: int(y) for x, y in self.start_time.items()}
        self.end_time = config['end_time']
        self.end_time = {x: int(y) for x, y in self.end_time.items()}
        self.session = requests.session()
        login_respond = self.session.post("https://cis.ncu.edu.tw/Course/main/login", user_info)
        if "Login successfully" in login_respond.text:
            print("Login successfully")
        else:
            raise ValueError("Error! Check your login config! Or issue the bug for me, thanks!")

    def get_calendar(self):
        # init Dataframe
        df = pd.read_html(self.session.get("https://cis.ncu.edu.tw/Course/main/personal/A4Crstable").text)[2]
        df = df.drop(index=[14, 15])
        df = df.drop(columns=['Unnamed: 0'])
        print(df)

        # init ics
        c = Calendar()
        c.add('prodid', 'Alan Li')
        c['summary'] = 'NCU'
        event_list = []
        previous_class = 'nan'

        # bad and dirty implement, i'm sorry :(
        with open('util/building_code.html') as f:
            raw_html = ''.join(f.readlines())
        locationCode = pd.read_html(raw_html)[0].iloc[5:, 1:3]
        locationCode = locationCode.dropna().T.reset_index(drop=True).T.reset_index(drop=True)
        locationCode = locationCode.set_index([0], drop=True).to_dict(orient='index')

        start_time = self.start_time
        end_time = self.end_time

        for day in range(0, 7):  # day of week
            for class_time in range(0, 14):  # 14 class time
                e = Event()

                if previous_class != df.iloc[class_time, day]:  # 這堂課變了
                    if str(previous_class) != 'nan':  # 上一個課程不是nan，結束上個活動
                        if class_time != 0:
                            event_list[-1].add('dtend',
                                               datetime(start_time['year'], start_time["month"],
                                                        start_time["day"] + day,
                                                        class_time + 7, 50, 0))
                        else:
                            event_list[-1].add('dtend',
                                               datetime(start_time['year'], start_time["month"],
                                                        start_time["day"] + day, 21,
                                                        50, 0))
                    if str(df.iloc[class_time, day]) != 'nan':  # 新的課不是nan
                        regex = re.compile(r'/ \((.+)\)')
                        rawClassData = regex.search(str(df.iloc[class_time, day]))
                        # print(rawLocation)
                        location = rawClassData.group(1)
                        regex = re.compile(r'(.{1,2})-')
                        code_name = regex.search(location).group(1)
                        location = locationCode[code_name][1] + ' ' + location
                        class_summary = str(df.iloc[class_time, day]).replace(rawClassData.group(0), "")
                        # print(f"summary:{classSummary}")
                        e.add('summary', class_summary)
                        e.add('location', location)
                        e.add('dtstart',
                              datetime(start_time['year'], start_time["month"], start_time["day"] + day, class_time + 8,
                                       0, 0))
                        alarm = Alarm()
                        alarm.add(name='action', value='DISPLAY')
                        alarm.add(name='trigger', value=timedelta(minutes=-self.announce_time))
                        e.add('rrule', {'freq': 'weekly',
                                        'until': datetime(end_time["year"], end_time["month"], end_time["day"],
                                                          class_time + 7,
                                                          0, 0)})
                        e.add_component(alarm)
                        event_list.append(e)

                previous_class = df.iloc[class_time, day]
        for event in event_list:  # combine all event
            c.add_component(event)
        name = no_dup(self.username)
        with open(f'schedule/{name}.ics', 'wb+') as f:
            f.write(c.to_ical())
        return name
