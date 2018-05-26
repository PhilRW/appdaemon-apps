import datetime
import functools

import appdaemon.plugins.hass.hassapi as hass


#
# App to turn on exhaust fan with high humidity and turn off after low humidity
#
# Use with constraints to activate only if night mode and/or manual override or equivalent is off
#
# Args:
#
# humidity_sensor: relative humidity sensor to control fan
# exhaust_fan: fan to exhaust humid air from room
# motion_sensor: (optional) binary sensor to determine occupancy
# backup_fan: (optional) fan to exhaust air that ignores occupancy
# rh_max: (optional) relative humidity level to activate the fan. default: 72
# rh_target: (optional) relative humidity level to deactivate the fan. default: 60
# motion_sensor_timeout: (optional) seconds to wait after motion sensor turns off to reactivate the fan. default: 34
#
#
#
# Release Notes
#
# Version 1.0:
#   Initial version
#       This version does not maintain its own state across restarts, so if you are editing this file after the fan has
#       been turned on, it will not automatically turn off the fan when the humidity reaches rh_target because
#       self.run_fan and self.switch_on are initialized to False.


class HumidityFan(hass.Hass):

    def initialize(self):
        self.log("initialize()", level="DEBUG")
        self.log("args: {0}".format(self.args), level="DEBUG")

        self.handle = None
        self.run_fan = False
        self.switch_on = False
        self.backup_switch_on = False
        self.rh_max = 60
        self.rh_target = 50
        self.motion_sensor_timeout = 60
        self.use_backup_switch = False

        if "humidity_sensor" and "exhaust_fan" in self.args:
            self.listen_state(self.humidity, self.args["humidity_sensor"])
            if "motion_sensor" in self.args:
                self.listen_state(self.motion, self.args["motion_sensor"])
                if "motion_sensor_timeout" in self.args:
                    self.motion_sensor_timeout = float(self.args["motion_sensor_timeout"])
            if "rh_max" in self.args:
                self.rh_max = float(self.args["rh_max"])
            if "rh_target" in self.args:
                self.rh_target = float(self.args["rh_target"])
        else:
            self.log("No humidity_sensor or exhaust_fan specified, doing nothing.", level="WARNING")

    def humidity(self, entity, attribute, old, new, kwargs):
        self.log("humidity({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level="DEBUG")

        if float(new) <= self.rh_target and self.run_fan:
            self.log("RH back to normal, stop exhausting humid air.", level="DEBUG")
            self.turn_off(self.args["exhaust_fan"])
            self.run_fan = False
        elif float(new) > self.rh_max and not self.run_fan:
            self.log("RH too high, start exhausting humid air.", level="DEBUG")
            self.run_fan = True
        else:
            self.log("Nothing to do.", level="DEBUG")

        if "motion_sensor" in self.args:
            self.check_motion(kwargs)
            if "backup_fan" in self.args:
                self.backup_fan_controller()
        else:
            self.fan_controller()

    def motion(self, entity, attribute, old, new, kwargs):
        self.log("motion({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level="DEBUG")

        if self.handle is not None:
            self.log("cancelling timer", level="DEBUG")
            self.cancel_timer(self.handle)
            self.handle = None

        if new == "on":
            if self.run_fan and self.switch_on:
                self.log("Fan is running, turning off switch...", level="DEBUG")
                self.turn_off(self.args["exhaust_fan"])
                self.switch_on = False
        elif new == "off":
            self.log("Wait {0} seconds for motion to stop...".format(self.motion_sensor_timeout), level="DEBUG")
            self.handle = self.run_in(self.check_motion, self.motion_sensor_timeout)
        else:
            self.log("Motion is neither on nor off: {0}".format(new), level="ERROR")

    def check_motion(self, kwargs):
        self.log("check_motion()", level="DEBUG")

        if "motion_sensor" in self.args and self.get_state(self.args["motion_sensor"]) == "off":
            entity = self.get_entity(self.args["motion_sensor"])
            last_changed = self.convert_utc(entity.last_changed)
            elapsed = (datetime.datetime.utcnow() - last_changed.replace(tzinfo=None)).seconds
            threshold = self.motion_sensor_timeout - 1

            if elapsed >= threshold:
                self.log("Motion has stayed inactive long enough since last check ({0} s): call fanController()".format(elapsed), level="DEBUG")
                self.fan_controller()
            else:
                self.log("Motion has not stayed inactive long enough since last check ({0} s): do nothing".format(elapsed), level="DEBUG")
        else:
            self.log("Motion is active: do nothing.", level="DEBUG")

    def fan_controller(self):
        self.log("fan_controller()", level="DEBUG")

        if self.run_fan and not self.switch_on:
            self.log("Turning on switch...", level="DEBUG")
            self.turn_on(self.args["exhaust_fan"])
            self.switch_on = True
        elif not self.run_fan and self.switch_on:
            self.log("Turning off switch...", level="DEBUG")
            self.turn_off(self.args["exhaust_fan"])
            self.switch_on = False
        else:
            self.log("Nothing to do.", level="DEBUG")

    def backup_fan_controller(self):
        self.log("backup_fan_controller()", level="DEBUG")

        if self.run_fan and not self.backup_switch_on:
            self.log("Turning on backup fan...", level="DEBUG")
            self.turn_on(self.args["backup_fan"])
            self.backup_switch_on = True
        elif not self.run_fan and self.backup_switch_on:
            self.log("Turning off backup fan...", level="DEBUG")
            self.turn_off(self.args["backup_fan"])
            self.backup_switch_on = False
        else:
            self.log("Nothing to do.", level="DEBUG")

    def get_entity(self, entity):
        self.log("get_entity({0})".format(entity), level="DEBUG")

        return functools.reduce(getattr, [self.entities] + entity.split('.'))
