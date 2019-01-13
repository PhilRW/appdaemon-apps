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
