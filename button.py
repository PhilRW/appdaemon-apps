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

        if "button" in self.args and \
                "dash" in self.args and \
                "timeout" in self.args and \
                "events" in self.args:
            self.listen_state(self.button_listener, self.args["button"])
        else:
            self.log("Missing required settings, doing nothing.", level="WARNING")

    def button_listener(self, entity, attribute, old, new, kwargs):
        self.log("button_listener({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=Translator.DEBUG_LEVEL)

        self.cancel_timer(self.handle)

        if new == "on":
            self.on_ts = datetime.datetime.now()
        elif new == "off":
            self.off_ts = datetime.datetime.now()
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

        if pattern in self.args["events"]:
            e = self.args["events"][pattern]
            self.log("Match found, firing event {0}".format(e))
            self.fire_event(e)

        self.presses = []
