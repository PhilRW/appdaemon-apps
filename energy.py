import appdaemon.appapi as appapi


class Allowance(appapi.AppDaemon):

    def initialize(self):
        self.log("initialize()", level="DEBUG")
        self.log("args: {0}".format(self.args), level="DEBUG")

        self.timeout = 600

        if "entity" in self.args:
            self.listen_state(self.allowance, self.args["entity"], timeout=self.args["timeout"])
            if "timeout" in self.args:
                self.timeout = int(self.args["timeout"])
        else:
            self.log("No entity specified, doing nothing.", level="WARNING")

    def allowance(self, entity, attribute, old, new, kwargs):
        self.log("allowance({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level="DEBUG")

        if new != old:
            if new == "on":
                self.handle = self.run_in(self.delayed_action, self.timeout)
            elif new == "off":
                self.log("Cancelling timer {0}".format(self.handle), level="DEBUG")
                self.cancel_timer(self.handle)

    def delayed_action(self, kwargs):
        self.log("turn_off()", level="DEBUG")

        self.turn_off(self.args["entity"])
