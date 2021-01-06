import datetime

import appdaemon.plugins.hass.hassapi as hass
import calendar

SHOULDER_START_HOUR = 13
PEAK_START_HOUR = 15
PEAK_END_HOUR = 19
# SHOULDER_END_HOUR = 21

SUMMER_MONTHS = [6, 7, 8, 9]
ON_PEAK = 'on-peak'
SHOULDER = 'shoulder'
OFF_PEAK = 'off-peak'

# PCCA = 0.00401
# DSMCA = 0.00159
# TCA = 0.00203
# CACJA = 0.00301

# ECA_ON_PEAK = 0.04170
# ECA_OFF_PEAK = 0.02574

RATE_SUMMER_ON_PEAK = 0.18527
RATE_SUMMER_SHOULDER = 0.13025
RATE_SUMMER_OFF_PEAK = 0.08018
RATE_WINTER_ON_PEAK = 0.19178
RATE_WINTER_SHOULDER = 0.13676
RATE_WINTER_OFF_PEAK = 0.08458


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
        tou_mode = OFF_PEAK
        lametric_icon = "a11218"
        if now.weekday() not in [5, 6] \
                and not self.is_holiday(now):
            if PEAK_END_HOUR > now.hour >= PEAK_START_HOUR:
                tou_mode = ON_PEAK
                lametric_icon = "a11217"
            elif PEAK_START_HOUR > now.hour >= SHOULDER_START_HOUR:
                tou_mode = SHOULDER
                lametric_icon = "a11219"

        attributes = {
            "lametric_icon": lametric_icon,
            "rate": self.get_rate(tou_mode)
        }

        if tou_mode != self.state:
            self.log("{0} is now {1}...".format(self.device, tou_mode), level="INFO")
            self.log("...with attributes: {0}".format(attributes), level="DEBUG")

            self.state = tou_mode
            self.set_state(self.device, state=tou_mode, attributes=attributes)

    def get_rate(self, tou_mode):
        self.log("get_rate({0})".format(tou_mode), level="DEBUG")

        rate = 0.00
        # eca = ECA_OFF_PEAK

        if tou_mode == ON_PEAK:
            # eca = ECA_ON_PEAK
            if datetime.datetime.now().month in SUMMER_MONTHS:
                rate = RATE_SUMMER_ON_PEAK
            else:
                rate = RATE_WINTER_ON_PEAK
        elif tou_mode == SHOULDER:
            if datetime.datetime.now().month in SUMMER_MONTHS:
                rate = RATE_SUMMER_SHOULDER
            else:
                rate = RATE_WINTER_SHOULDER
        elif tou_mode == OFF_PEAK:
            if datetime.datetime.now().month in SUMMER_MONTHS:
                rate = RATE_SUMMER_OFF_PEAK
            else:
                rate = RATE_WINTER_OFF_PEAK

        # return rate + eca + PCCA + DSMCA + TCA + CACJA
        return rate
