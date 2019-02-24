import datetime
import random

import appdaemon.plugins.hass.hassapi as hass


class TempToHue(hass.Hass):
    DEBUG_LEVEL = "DEBUG"

    def initialize(self):
        self.log("initialize()", level=TempToHue.DEBUG_LEVEL)
        self.log("args: {0}".format(self.args), level=TempToHue.DEBUG_LEVEL)

        self.low_hue = 240
        self.high_hue = 360

        if "temperature_sensor" in self.args and \
                "low_temp" in self.args and \
                "high_temp" in self.args and \
                "output_entity" in self.args:
            self.listen_state(self.set_hue, self.args["temperature_sensor"])
        else:
            self.log("Missing required settings, doing nothing.", level="WARNING")

    def set_hue(self, entity, attribute, old, new, kwargs):
        self.log("button_listener({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=TempToHue.DEBUG_LEVEL)

        low = float(self.args["low_temp"])
        high = float(self.args["high_temp"])

        if new != old:
            x1 = low
            x2 = high
            y1 = self.low_hue
            y2 = self.high_hue

            slope = (y2 - y1) / (x2 - x1)
            b = y1 - (x1 * slope)
            hue = (slope * float(new)) + b

            if hue < self.low_hue:
                hue = self.low_hue
            elif hue > self.high_hue:
                hue = self.high_hue

            hue = round(hue)

            self.set_state(self.args["output_entity"], state=hue, attributes={"unit_of_measurement": "°"})


class DailyColorName(hass.Hass):
    DEBUG_LEVEL = "DEBUG"

    def initialize(self):
        self.log("initialize()", level=DailyColorName.DEBUG_LEVEL)
        self.log("args: {0}".format(self.args), level=DailyColorName.DEBUG_LEVEL)

        self.low_hue = 240
        self.high_hue = 360

        if "entity_id" in self.args and \
                "default_color_names" in self.args:
            self.run_daily(self.set_color_name, datetime.time(3, 0))
            self.log("Will run at next 03:00.", level="INFO")
            self.set_color_name(None)
        else:
            self.log("Missing required settings, doing nothing.", level="WARNING")

    def set_color_name(self, kwargs):
        self.log("set_color_name({0})".format(kwargs), level=DailyColorName.DEBUG_LEVEL)

        cn = random.choice(self.args["default_color_names"])
        eid = self.args["entity_id"]

        self.log("Today's random default color is {0}".format(cn), level=DailyColorName.DEBUG_LEVEL)

        dt_t = datetime.datetime.today()
        today = datetime.datetime(year=dt_t.year, month=dt_t.month, day=dt_t.day)

        if "rules" in self.args:
            for r in self.args["rules"]:
                self.log("Evaluating rule for {0}.".format(r["name"]), level=DailyColorName.DEBUG_LEVEL)
                if r["type"] == "dom":
                    self.log("Type is 'dom': month = {0}, day = {1}".format(r["month"], r["day"]), level=DailyColorName.DEBUG_LEVEL)
                    if today == datetime.datetime(year=dt_t.year, month=r["month"], day=r["day"]):
                        self.log("Today is {0}.".format(r["name"]), level=DailyColorName.DEBUG_LEVEL)
                        cn = r["color_name"]
                        break
                if r["type"] == "eval":
                    self.log("Type is 'state': eval = {0}, value = {1}".format(r["eval"], r["values"]), level=DailyColorName.DEBUG_LEVEL)
                    s = eval(r["eval"])
                    if s in r["values"]:
                        self.log("Today is {0}.".format(r["name"]), level=DailyColorName.DEBUG_LEVEL)
                        cn = r["color_name"]
                        break

        self.log("Setting {0} to {1}.".format(eid, cn), level=DailyColorName.DEBUG_LEVEL)
        self.set_state(eid, state=cn)
