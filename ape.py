import bisect
import calendar
import pickle

import appdaemon.appapi as appapi
import datetime


class Event:

    def __init__(self, dt, entity, new):
        self.dt = dt
        self.entity = entity
        self.new = new

    def __str__(self):
        return "event({0}, {1}, {2})".format(self.dt, self.entity, self.new)

    def __repr__(self):
        return "<event({0}, {1}, {2})>".format(self.dt, self.entity, self.new)


class Monkey(appapi.AppDaemon):
    EVENTS_DB = "Monkey_events"

    def initialize(self):
        self.log("initialize()", level="INFO")
        self.log("args: {0}".format(self.args), level="INFO")

        if "input_select" in self.args \
                and "entities" in self.args \
                and "see_mode" in self.args \
                and "do_mode" in self.args:

            self.events = self.load(Monkey.EVENTS_DB)
            if self.events is None:
                self.log("No events pickle file found, starting from scratch.", level="INFO")
                self.forget(None, None, None)
            self.log("events: {0}".format(self.events), level="INFO")

            self.observations = []
            self.do_handles = []

            self.listen_state(self.decide, self.args["input_select"])
            if "forget_event" in self.args:
                self.listen_event(self.forget, self.args["forget_event"])

            for e in self.args["entities"]:
                self.listen_state(self.monkey_see, e, constrain_input_select="{0},{1}".format(self.args["input_select"], self.args["see_mode"]))
        else:
            self.log("Missing required parameter(s). Cannot continue.", level="ERROR")

    def decide(self, entity, attribute, old, new, kwargs):
        self.log("decide({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level="INFO")

        if new == self.args["see_mode"]:
            # cancel all scheduled "do" callbacks
            for h in self.do_handles:
                self.cancel_timer(h)
            self.log("cancelled {0} monkey_do handle(s)".format(len(self.do_handles)), level="INFO")
            self.do_handles = []
        elif new == self.args["do_mode"]:
            # remember anything we may have seen
            self.remember()

            # schedule callbacks to replay what happened
            self.schedule_today(None)

            when = datetime.time(0, 0)
            h = self.run_daily(self.schedule_today, when)
            self.do_handles.append(h)
        else:
            self.log("{0} is {1}, nothing to see or do".format(self.args["input_select"], new))

    def monkey_see(self, entity, attribute, old, new, kwargs):
        self.log("monkey_see({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level="INFO")

        if new != old:
            self.log("appending event to observations...", level="INFO")
            e = Event(datetime.datetime.now(), entity, new)
            self.observations.append(e)

            self.log("...{0} observation(s): {1}".format(len(self.observations), self.observations), level="INFO")

    def monkey_do(self, kwargs):
        self.log("do({0})".format(kwargs), level="INFO")

        evnt = kwargs["evnt"]
        self.log("replaying {0}".format(evnt), level="INFO")

        if evnt.new == "on":
            self.turn_on(evnt.entity)
        elif evnt.new == "off":
            self.turn_off(evnt.entity)
        else:
            self.log("\"new\" was neither \"on\" nor \"off\": {0}".format(evnt.new), level="ERROR")

    def remember(self):
        self.log("remember()", level="INFO")

        self.log("observations to remember: {0}".format(self.observations), level="INFO")

        days = {}
        for i in range(0, 7):
            days[i] = []

        for e in self.observations:
            days[e.dt.weekday()].append(e)

        self.log("observations as days: {0}".format(days), level="INFO")

        for i in range(0, 7):
            try:
                self.log("Remembering events from {0}...".format(calendar.day_name[i]), level="INFO")
                left = bisect.bisect_left([e.dt for e in self.events[i]], days[i][0].dt)
                right = bisect.bisect_right([e.dt for e in self.events[i]], days[i][-1].dt)
                self.events[i] = self.events[i][:left] + days[i] + self.events[i][right:]
                self.log("...new events for {0} = {1}".format(calendar.day_name[i], self.events[i]), level="INFO")
            except IndexError:
                self.log("...{0} has no events yet. Skipping.".format(calendar.day_name[i]), level="INFO")

        self.save(self.events, Monkey.EVENTS_DB)
        self.observations = []

    def schedule_today(self, kwargs):
        self.log("schedule_today({0})".format(kwargs), level="INFO")

        today = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        for e in self.events[today.weekday()]:
            # TODO: add randomness
            time = e.dt.time()
            dt = datetime.datetime.combine(today.date(), time)
            if dt > datetime.datetime.now() + datetime.timedelta(seconds=5):
                h = self.run_at(self.monkey_do, dt, evnt=e)
                self.do_handles.append(h)
            else:
                self.log("event occurs in past, skipping ({0})...".format(time), level="INFO")

    def forget(self, event_name, data, kwargs):
        self.log("forget({0}, {1}, {2})".format(event_name, data, kwargs), level="INFO")

        self.events = {}
        for i in range(0, 7):
            self.events[i] = []

        self.save(self.events, Monkey.EVENTS_DB)

    def save(self, obj, name):
        self.log(msg="save({0}, {1})".format(obj, name), level="INFO")

        with open(name + '.pkl', 'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    def load(self, name):
        self.log(msg="load({0})".format(name), level="INFO")

        try:
            with open(name + '.pkl', 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None
