import datetime

import appdaemon.plugins.hass.hassapi as hass


class WakeUp(hass.Hass):

    def initialize(self):
        self.log("initialize()", level="DEBUG")

        self.duration = 1800.0
        self.running = False
        self.start_time = None
        self.start_brightness = 0
        self.end_brightness = 255
        self.handle = None

        if "light" in self.args and "trigger_event" in self.args:
            self.listen_event(self.kickoff, self.args["trigger_event"])
            self.listen_state(self.cancel, self.args["light"], new="off")

            if "duration" in self.args:
                self.duration = float(self.args["duration"])
            else:
                self.log("No duration provided, going with default.", level="INFO")

            if "start_brightness" in self.args:
                self.start_brightness = int(self.args["start_brightness"])

            if "end_brightness" in self.args:
                self.end_brightness = int(self.args["end_brightness"])
        else:
            self.log("No light or trigger event specified. Doing nothing.", level="ERROR")

    def kickoff(self, event_name, data, kwargs):
        self.log("kickoff")
        self.log("kickoff({0}, {1}, {2})".format(event_name, data, kwargs), level="DEBUG")

        self.running = True
        self.start_time = datetime.datetime.now()
        self.run_in(self.dim_up, 1)

    def dim_up(self, kwargs):
        self.log("dim_up({0})".format(kwargs), level="DEBUG")
        self.log("dim up")

        elapsed = (datetime.datetime.now() - self.start_time).seconds

        floor = ((self.duration - elapsed) / self.duration) * self.start_brightness

        if self.running and elapsed <= self.duration:
            brightness = int(((elapsed / self.duration) * self.end_brightness) + floor)
            self.call_service("light/turn_on", entity_id=self.args["light"], brightness=brightness)
            self.handle = self.run_in(self.dim_up, 1)
        else:
            self.running = False

    def cancel(self, entity, attribute, old, new, kwargs):
        self.log("cancel({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level="DEBUG")
        self.log("Cancel")

        self.running = False
        if self.handle is not None:
            self.cancel_timer(self.handle)
