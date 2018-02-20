import calendar
import datetime
import requests
import base64
import json
import appdaemon.appapi as appapi


class ScreensaverController(appapi.AppDaemon):

    def initialize(self):
        self.log("initialize()", level="DEBUG")
        self.log("args: {0}".format(self.args), level="DEBUG")

        self.url = "http://{0}:8080/api/v2/device/display".format(self.args["device_ip"])
        creds = "{0}:{1}".format("dev", self.args["api_key"]).encode(("UTF-8"))
        self.auth = base64.b64encode(creds)

        self.listen_event(self.sleep, self.args["sleep_event"])
        self.listen_event(self.wake, self.args["wake_event"])

    def sleep(self, event_name, data, kwargs):
        self.log("sleep({0}, {1}, {2}".format(event_name, data, kwargs), level="DEBUG")
        self.log("Sleeping LaMetric".format())
        self.send(True)

    def wake(self, event_name, data, kwargs):
        self.log("wake({0}, {1}, {2}".format(event_name, data, kwargs), level="DEBUG")
        self.log("Waking LaMetric".format())
        self.send(False)

    def send(self, sleep):
        self.log("send({0})".format(sleep), level="DEBUG")

        data = {
            "screensaver": {
                "enabled": sleep,
            }
        }
        headers = {
            "Authorization": "Basic {0}".format(self.auth.decode("ascii"))
        }

        response = requests.put(self.url, json.dumps(data), headers=headers)
        if response.status_code != 200:
            self.log("Trouble sending command to LaMetric: {0} {1}".format(response.status_code, response.status_code), level="ERROR")


class Holiday(object):
    def __init__(self, name, month, dow=None, wom=None, day=None):
        '''

        :param name: the name of the holiday
        :param month: month of the holiday (1 = January)
        :param dow: day of the week of the holiday (0-indexed, starting with Monday)
        :param wom: week of the month of the holiday (0-indexed, use -1 for last)
        :param day: day of the month (of dow and wom are not used)
        '''
        self.name = name
        self.month = month
        self.dow = dow
        self.wom = wom
        self.day = day
        self.dt = None
        self.year = datetime.datetime.now().year
        self.__parse_holiday()

    def __parse_holiday(self):
        if self.day is not None:
            self.dt = datetime.datetime(self.year, self.month, self.day)
            if self.dt.weekday() == 5:
                self.dt = self.dt - datetime.timedelta(days=1)
            elif self.dt.weekday() == 6:
                self.dt = self.dt + datetime.timedelta(days=1)
        elif self.dow is not None \
                and self.wom is not None:
            month_cal = calendar.monthcalendar(self.year, self.month)
            found_weeks = []
            for week in month_cal:
                if week[self.dow] != 0:
                    found_weeks.append(week)
            day = (found_weeks[self.wom][self.dow])
            self.dt = datetime.datetime(self.year, self.month, day)


class EnergyApp(appapi.AppDaemon):

    def initialize(self):
        self.log("initialize()", level="DEBUG")
        self.log("args: {0}".format(self.args), level="DEBUG")

        self.min_power = 0
        self.max_power = 0
        self.energy_offset = 0
        self.chart_readings = [0] * 37
        self.chart_refresh = 2335
        self.handle = None

        self.frame_power = None
        self.frame_energy = None
        self.frame_chart = None
        self.frame_tou = None

        if "power_meter" in self.args \
                and "energy_meter" in self.args \
                and "lametric_app_id" in self.args \
                and "lametric_access_token" in self.args:
            self.listen_state(self.power, self.args["power_meter"])
            self.listen_state(self.energy, self.args["energy_meter"])
            self.app_id = self.args["lametric_app_id"]
            self.access_token = self.args["lametric_access_token"]
        else:
            self.log("Required parameter(s) missing, doing nothing.", level="WARNING")

        if "energy_offset" in self.args:
            self.energy_offset = float(self.args["energy_offset"])

        if "chart_refresh" in self.args:
            self.chart_refresh = int(self.args["chart_refresh"])

        # update the chart data
        self.run_every(self.chart, datetime.datetime.now(), self.chart_refresh)

        # update the display hourly on the 0-minute at a minimum (for TOU)
        # time() object defaults to time(0, 0)
        self.run_hourly(self.update, datetime.time())

    def power(self, entity, attribute, old, new, kwargs):
        self.log("power({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level="DEBUG")

        w = float(new)

        # i14431 is green, 144432 is red
        icon_sel = "i14431" if w <= 0 else "i14432"

        if w > self.max_power:
            self.max_power = w
        elif w < self.min_power:
            self.min_power = w

        self.frame_power = {
            "goalData": {
                "start": self.min_power,
                "current": w,
                "end": self.max_power,
                "unit": "W"
            },
            "icon": icon_sel
        }

        if self.handle is not None:
            self.log("cancelling timer", level="DEBUG")
            self.cancel_timer(self.handle)
            self.handle = None
        self.handle = self.run_in(self.update, 3)

    def energy(self, entity, attribute, old, new, kwargs):
        self.log("energy({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level="DEBUG")

        kWh = float(new) + self.energy_offset

        self.frame_energy = {
            "text": "{0} kWH".format(round(kWh))
        }

    def chart(self, kwargs):
        self.log("update_chart({0})".format(kwargs), level="DEBUG")

        cur_power = float(self.get_state(self.args["power_meter"]))

        self.chart_readings.pop(0)
        self.chart_readings.append(cur_power)

        points = []
        for r in self.chart_readings:
            points.append(int(r + abs(self.min_power)))

        self.frame_chart = {
            "chartData": points
        }

    def tou(self):
        self.log("tou()", level="DEBUG")

        now = datetime.datetime.now()
        if 18 > now.hour >= 14 \
                and now.weekday() not in [5, 6] \
                and not self.is_holiday(now):
            text = "on-peak"
            icon = "a11217"
        elif 21 > now.hour >= 9:
            text = "shoulder"
            icon = "a11219"
        else:
            text = "off-peak"
            icon = "a11218"

        self.frame_tou = {
            "text": text,
            "icon": icon
        }

    def build_frames(self):
        self.log("build_frames()", level="DEBUG")

        frames = []
        if self.frame_power: frames.append(self.frame_power)
        if self.frame_energy: frames.append(self.frame_energy)
        if self.frame_chart: frames.append(self.frame_chart)
        if self.frame_tou: frames.append(self.frame_tou)

        self.frames = {
            "frames": frames
        }
        self.log("frames: {0}".format(frames), level="DEBUG")

    def is_holiday(self, dt):
        self.log("is_holiday({0})".format(dt), level="DEBUG")

        tou_holidays = [
            Holiday("New Year's Day", 1, day=1),
            Holiday("Memorial Day", 5, dow=0, wom=-1),
            Holiday("Independence Day", 7, day=4),
            Holiday("Labor Day", 9, dow=0, wom=0),
            Holiday("Thanksgiving Day", 11, dow=3, wom=3),
            Holiday("Christmas Day", 12, day=25)
        ]

        return dt.date() in [h.dt.date() for h in tou_holidays]

    def update(self, kwargs):
        self.log("update()", level="DEBUG")

        self.tou()
        self.build_frames()

        self.log("Sending updated data to LaMetric...", level="DEBUG")
        url = "https://developer.lametric.com/api/v1/dev/widget/update/com.lametric.{0}/1".format(self.app_id)
        headers = {"X-Access-Token": self.access_token}
        result = requests.post(url, json.dumps(self.frames), headers=headers)
        self.log("status_code: {0}, reason: {1}".format(result.status_code, result.reason), level="DEBUG")

        if result.status_code != 200:
            self.log("Problem sending to LaMetric: status_code: {0}, reason: {1}".format(result.status_code, result.reason), level="ERROR")

        self.handle = None
