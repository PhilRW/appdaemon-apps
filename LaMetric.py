import base64
import datetime
import json

import appdaemon.plugins.hass.hassapi as hass
import pytz
import requests
import dateutil.parser
import time

class ScreensaverController(hass.Hass):

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


class EnergyApp(hass.Hass):
    DEBUG_LEVEL = "DEBUG"

    def initialize(self):
        self.log("initialize()", level=EnergyApp.DEBUG_LEVEL)
        self.log("args: {0}".format(self.args), level=EnergyApp.DEBUG_LEVEL)

        self.min_power = 0
        self.max_power = 0
        self.energy_offset = 0
        self.chart_readings = []
        self.chart_refresh = 2335
        self.handle = None

        self.frame_power = None
        self.frame_energy = None
        self.frame_chart = None
        self.frame_tou = None

        if "lametric_app_id" and "lametric_access_token" in self.args:
            if "power_meter" in self.args:
                self.listen_state(self.power, self.args["power_meter"])
                if "chart_refresh" in self.args:
                    self.chart_refresh = int(self.args["chart_refresh"])
                # update the chart data
                self.run_every(self.chart, datetime.datetime.now(), self.chart_refresh)
            if "energy_meter" in self.args:
                self.listen_state(self.energy, self.args["energy_meter"])
                if "energy_offset" in self.args:
                    self.energy_offset = float(self.args["energy_offset"])
            self.app_id = self.args["lametric_app_id"]
            self.access_token = self.args["lametric_access_token"]
        else:
            self.log("Required parameter(s) missing, doing nothing.", level="WARNING")

        if "tou_mode" in self.args:
            self.listen_state(self.tou, self.args["tou_mode"])

        # update the display hourly on the 0-minute at a minimum (for TOU)
        # time() object defaults to time(0, 0)
        self.run_hourly(self.update, datetime.time())

        self.tou(None, None, None, self.get_state(self.args["tou_mode"]), None)

    def power(self, entity, attribute, old, new, kwargs):
        self.log("power({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=EnergyApp.DEBUG_LEVEL)

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
            self.log("cancelling timer", level=EnergyApp.DEBUG_LEVEL)
            self.cancel_timer(self.handle)
            self.handle = None
        self.handle = self.run_in(self.update, 3)

    def energy(self, entity, attribute, old, new, kwargs):
        self.log("energy({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=EnergyApp.DEBUG_LEVEL)

        kWh = float(new) + self.energy_offset

        self.frame_energy = {
            "text": "{0} kWH".format(round(kWh))
        }

    def chart(self, kwargs):
        self.log("update_chart({0})".format(kwargs), level=EnergyApp.DEBUG_LEVEL)

        try:
            cur_power = float(self.get_state(self.args["power_meter"]))
        except ValueError:
            cur_power = 0

        while len(self.chart_readings) > 36:
            self.chart_readings.pop(0)
        self.chart_readings.append(cur_power)

        points = []
        for r in self.chart_readings:
            points.append(int(r + abs(self.min_power)))

        self.frame_chart = {
            "chartData": points
        }

    def tou(self, entity, attribute, old, new, kwargs):
        self.log("tou({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=EnergyApp.DEBUG_LEVEL)

        if new != old:
            text = new
            icon = self.get_state(self.args["tou_mode"], attribute="lametric_icon")
            self.log("TOU info is {0}".format(text), level=EnergyApp.DEBUG_LEVEL)

            self.frame_tou = {
                "text": text,
                "icon": icon
            }

            self.handle = self.run_in(self.update, 5)

    def build_frames(self):
        self.log("build_frames()", level=EnergyApp.DEBUG_LEVEL)

        frames = []
        if self.frame_power: frames.append(self.frame_power)
        if self.frame_energy: frames.append(self.frame_energy)
        if self.frame_chart: frames.append(self.frame_chart)
        if self.frame_tou: frames.append(self.frame_tou)

        self.frames = {
            "frames": frames
        }
        self.log("frames: {0}".format(frames), level=EnergyApp.DEBUG_LEVEL)

    def update(self, kwargs):
        self.log("update()", level=EnergyApp.DEBUG_LEVEL)

        self.build_frames()

        self.log("Sending updated data to LaMetric...", level=EnergyApp.DEBUG_LEVEL)
        url = "https://developer.lametric.com/api/v1/dev/widget/update/com.lametric.{0}/1".format(self.app_id)
        headers = {"X-Access-Token": self.access_token}
        try:
            result = requests.post(url, json.dumps(self.frames), headers=headers, timeout=5)
            self.log("status_code: {0}, reason: {1}".format(result.status_code, result.reason), level=EnergyApp.DEBUG_LEVEL)

            if result.status_code != 200:
                self.log("Problem sending to LaMetric: status_code: {0}, reason: {1}".format(result.status_code, result.reason), level="ERROR")
        except requests.exceptions.ConnectionError as e:
            self.log("Problem connecting to LaMetric: {0}".format(e), level="ERROR")
            self.handle = self.run_in(self.update, 5)

        self.handle = None


class TaskApp(hass.Hass):
    DEBUG_LEVEL = "INFO"

    def initialize(self):
        self.log("initialize()", level=TaskApp.DEBUG_LEVEL)
        self.log("args: {0}".format(self.args), level=TaskApp.DEBUG_LEVEL)

        if "lametric_app_id" \
                and "lametric_access_token" \
                and "todoist_project_id" \
                and "todoist_token" in self.args:
            self.app_id = self.args["lametric_app_id"]
            self.lametric_token = self.args["lametric_access_token"]
            self.project_id = self.args["todoist_project_id"]
            self.todoist_token = self.args["todoist_token"]
        else:
            self.log("Required parameter(s) missing, doing nothing.", level="WARNING")

        self.run_hourly(self.update, datetime.time())
        self.update(None)

    def get_tasks(self):
        self.log("get_tasks()", level=TaskApp.DEBUG_LEVEL)

        tasks = []
        try:
            tz = pytz.timezone(self.get_plugin_config()["time_zone"])
        except Exception as e:
            self.log(e, level="ERROR")
            raise e

        r = requests.get(
            "https://api.todoist.com/rest/v1/tasks",
            params={
                "project_id": self.project_id
            },
            headers={
                "Authorization": "Bearer %s" % self.todoist_token
            }).json()

        for task in r:
            self.log("task found: {0}".format(task), level=TaskApp.DEBUG_LEVEL)
            if 'due' in task:
                try:
                    t_tz = task['due']['timezone']
                    t_dt = task['due']['datetime']
                    dt = dateutil.parser.parse(t_dt).astimezone(pytz.timezone(t_tz))
                except:
                    self.log("except...")
                    dt = datetime.datetime.strptime(task['due']['date'], "%Y-%m-%d").astimezone(tz)
                    dt += datetime.timedelta(days=1)

                self.log(f"parsed dt: {dt}, now: {datetime.datetime.now(tz)}", level=TaskApp.DEBUG_LEVEL)

                if dt < datetime.datetime.now(tz):
                    self.log("adding task to task list: {0}".format(task['content']), level=TaskApp.DEBUG_LEVEL)
                    tasks.append(task['content'])

        return tasks

    def build_frames(self):
        self.log("build_frames()", level=TaskApp.DEBUG_LEVEL)

        tasks = self.get_tasks()
        self.log("tasks: {0}".format(tasks), level=TaskApp.DEBUG_LEVEL)

        i = 0

        frames = [{
            "text": "no todo",
            "icon": "a87",
            "index": i
        }]

        if len(tasks) > 0:
            frames = [{
                "text": "Todo:",
                "icon": "a6601",
                "index": i
            }]

            for task in tasks:
                i += 1
                frames.append({
                    "text": task,
                    "index": i
                })

        self.frames = {
            "frames": frames
        }

        self.log("frames: {0}".format(frames), level=TaskApp.DEBUG_LEVEL)

    def update(self, kwargs):
        self.log("update({0})".format(kwargs), level=TaskApp.DEBUG_LEVEL)

        self.build_frames()

        self.log("Sending updated data to LaMetric...", level=TaskApp.DEBUG_LEVEL)

        host = "developer.lametric.com"
        if "device_ip" in self.args:
            host = "{0}:4343".format(self.args["device_ip"])

        url = "https://{0}/api/v1/dev/widget/update/com.lametric.{1}/1".format(host, self.app_id)
        headers = {"X-Access-Token": self.lametric_token}
        try:
            result = requests.post(url, json.dumps(self.frames), headers=headers, verify=("device_ip" not in self.args))
            self.log("status_code: {0}, reason: {1}".format(result.status_code, result.reason), level=TaskApp.DEBUG_LEVEL)

            if result.status_code != 200:
                self.log("Problem sending to LaMetric: status_code: {0}, reason: {1}".format(result.status_code, result.reason), level="ERROR")
        except requests.exceptions.ConnectionError as e:
            self.log("Problem connecting to LaMetric: {0}".format(e), level="ERROR")
            self.handle = self.run_in(self.update, 55)

        self.handle = None
