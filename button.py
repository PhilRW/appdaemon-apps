import datetime

import appdaemon.plugins.hass.hassapi as hass


class Translator(hass.Hass):
    DEBUG_LEVEL = "DEBUG"

    def initialize(self):
        self.log("initialize()", level=Translator.DEBUG_LEVEL)
        self.log("args: {0}".format(self.args), level=Translator.DEBUG_LEVEL)

        self.on_ts = None
        self.off_ts = None
        self.presses = []
        self.handle = None
        self.light_mode = False

        if "button" in self.args and \
                "dash" in self.args and \
                "timeout" in self.args and \
                "events" in self.args:
            self.listen_state(self.button_listener, self.args["button"])
            if "light_mode_event" in self.args and \
                    "lights" in self.args:
                self.listen_event(self.light_mode_listener, self.args["light_mode_event"])
        else:
            self.log("Missing required settings, doing nothing.", level="WARNING")

    def light_mode_listener(self, event_name, data, kwargs):
        self.log("light_mode_listener({0}, {1}, {2})".format(event_name, data, kwargs), level=Translator.DEBUG_LEVEL)

        self.light_mode = not self.light_mode

    def button_listener(self, entity, attribute, old, new, kwargs):
        self.log("button_listener({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=Translator.DEBUG_LEVEL)

        self.cancel_timer(self.handle)

        if new == "on":
            self.on_ts = datetime.datetime.now()
            if self.light_mode:
                for e in self.args["lights"]:
                    self.turn_on(e)
        elif new == "off":
            self.off_ts = datetime.datetime.now()
            if self.light_mode:
                for e in self.args["lights"]:
                    self.turn_off(e)
            dur = self.off_ts - self.on_ts
            self.log("Duration: {0}".format(dur), level=Translator.DEBUG_LEVEL)
            self.presses.append(dur)
            self.handle = self.run_in(self.button_finished, self.args["timeout"])

    def button_finished(self, kwargs):
        self.log("button_finished({0})".format(kwargs), level=Translator.DEBUG_LEVEL)

        self.log("Presses: {0}".format(self.presses), level=Translator.DEBUG_LEVEL)

        pattern = ""

        for p in self.presses:
            if p > datetime.timedelta(seconds=self.args["dash"]):
                pattern += "-"
            else:
                pattern += "."

        self.log("Pattern: {0}".format(pattern))

        if self.args["events"] and pattern in self.args["events"]:
            e = self.args["events"][pattern]
            self.log("Match found: {0} == {1}".format(pattern, e))
            if (not self.light_mode) or \
                    ("light_mode_event" in self.args and e == self.args["light_mode_event"]):
                self.log("Firing event {0}".format(e))
                self.fire_event(e)
            else:
                self.log("Not firing event because light_mode is {0}".format(self.light_mode))

        self.presses = []
