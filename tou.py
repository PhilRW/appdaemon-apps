import calendar
import datetime

import appdaemon.plugins.hass.hassapi as hass


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


class StateManagerXcelColorado(hass.Hass):

    def initialize(self):
        self.log("initialize()", level="DEBUG")
        self.log("args: {0}".format(self.args), level="INFO")

        self.device = None
        self.state = None

        if "device" in self.args:
            self.device = self.args["device"]
            self.run_hourly(self.update_state, datetime.time())
            self.update_state(None)
        else:
            self.log("No device specified. Doing nothing.", level="ERROR")

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

    def update_state(self, kwargs):
        self.log("update_state({0})".format(kwargs), level="DEBUG")

        now = datetime.datetime.now()
        if 18 > now.hour >= 14 \
                and now.weekday() not in [5, 6] \
                and not self.is_holiday(now):
            tou_mode = "on-peak"
            lametric_icon = "a11217"
        elif 21 > now.hour >= 9:
            tou_mode = "shoulder"
            lametric_icon = "a11219"
        else:
            tou_mode = "off-peak"
            lametric_icon = "a11218"

        attributes = {"lametric_icon": lametric_icon}

        if tou_mode != self.state:
            self.log("{0} is now {1}...".format(self.device, tou_mode), level="INFO")
            self.log("...with attributes: {0}".format(attributes), level="DEBUG")

            self.state = tou_mode
            self.set_state(self.device, state=tou_mode, attributes=attributes)
