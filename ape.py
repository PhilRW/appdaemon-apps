import bisect
import calendar
import datetime
import pickle

import appdaemon.plugins.hass.hassapi as hass


class Event:

    def __init__(self, dt, entity, new):
        self.dt = dt
        self.entity = entity
        self.new = new

    def __str__(self):
        return "event({0}, {1}, {2})".format(self.dt, self.entity, self.new)

    def __repr__(self):
        return "<event({0}, {1}, {2})>".format(self.dt, self.entity, self.new)


class Monkey(hass.Hass):

    DEBUG_LEVEL="INFO"

    def initialize(self):
        self.log("initialize()", level=Monkey.DEBUG_LEVEL)
        self.log("args: {0}".format(self.args), level="INFO")

        if "occupancy_state" in self.args \
                and "entities" in self.args:

            self.events_db = "/share/Monkey_events"
            if "events_db" in self.args:
                self.events_db = self.args["events_db"]

            self.events = self.load(self.events_db)
            self.log("post event-load", level=Monkey.DEBUG_LEVEL)
            if self.events is None:
                self.log("No events pickle file found, starting from scratch.", level="WARNING")
                self.forget(None, None, None)
            self.log("{0} events loaded".format(self.len_d(self.events)), level="INFO")

            self.observations = []
            self.do_handles = []
            self.watching = None

            self.listen_state(self.decide, self.args["occupancy_state"])
            if "forget_event" in self.args:
                self.listen_event(self.forget, self.args["forget_event"])

            for e in self.args["entities"]:
                self.listen_state(self.monkey_see, e)

            self.exit_delay = 60
            if "exit_delay" in self.args:
                self.exit_delay = int(self.args["exit_delay"])

            os = self.get_state(self.args["occupancy_state"])
            self.decide(None, None, None, os, None)

        else:
            self.log("Missing required parameter(s). Cannot continue.", level="ERROR")

    def decide(self, entity, attribute, old, new, kwargs):
        self.log("decide({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=Monkey.DEBUG_LEVEL)

        if new == 'on':
            # cancel all scheduled "do" callbacks
            for h in self.do_handles:
                self.cancel_timer(h)
            self.log("cancelled {0} monkey_do handle(s)".format(len(self.do_handles)), level="INFO")
            self.do_handles = []

            # start observing
            self.watching = True
        elif new == 'off':
            # delay to start doing things until things have settled
            h = self.run_in(self.start_doing, self.exit_delay)
            self.do_handles.append(h)
        else:
            self.log("{0} is {1}, nothing to see or do".format(self.args["occupancy_state"], new))

    def start_doing(self, kwargs):
        self.log("start_doing({0})".format(kwargs), level=Monkey.DEBUG_LEVEL)

        # stop observing
        self.watching = False

        # remember anything we may have seen
        self.remember()

        # schedule callbacks to replay what happened
        self.schedule_today(None)

        when = datetime.time(0, 0)
        h = self.run_daily(self.schedule_today, when)
        self.do_handles.append(h)

    def monkey_see(self, entity, attribute, old, new, kwargs):
        self.log("monkey_see({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=Monkey.DEBUG_LEVEL)

        if self.watching and new != old:
            self.log("appending event to observations...", level="INFO")
            e = Event(datetime.datetime.now(), entity, new)
            self.observations.append(e)

            self.log("...{0} observation(s)...".format(len(self.observations)), level="INFO")
            self.log("...{0}".format(self.observations), level=Monkey.DEBUG_LEVEL)

    def monkey_do(self, kwargs):
        self.log("do({0})".format(kwargs), level=Monkey.DEBUG_LEVEL)

        evnt = kwargs["evnt"]
        self.log("replaying {0}".format(evnt), level="INFO")

        if evnt.new == "on":
            self.turn_on(evnt.entity)
        elif evnt.new == "off":
            self.turn_off(evnt.entity)
        else:
            self.log("\"new\" was neither \"on\" nor \"off\": {0}".format(evnt.new), level="WARNING")

    def remember(self):
        self.log("remember()", level=Monkey.DEBUG_LEVEL)

        self.log("{0} observations to remember...".format(len(self.observations)), level="INFO")
        self.log("...{0}".format(self.observations), level=Monkey.DEBUG_LEVEL)

        days = {}
        for i in range(0, 7):
            days[i] = []

        for e in self.observations:
            days[e.dt.weekday()].append(e)

        self.log("observations as days: {0}".format(days), level=Monkey.DEBUG_LEVEL)

        for i in range(0, 7):
            try:
                self.log("Remembering events from {0}...".format(calendar.day_name[i]), level="INFO")
                left = bisect.bisect_left([e.dt.time() for e in self.events[i]], days[i][0].dt.time())
                right = bisect.bisect_right([e.dt.time() for e in self.events[i]], days[i][-1].dt.time())
                self.events[i] = self.events[i][:left] + days[i] + self.events[i][right:]
                self.log("...{0} events for {1} now...".format(len(self.events), calendar.day_name[i]), level="INFO")
                self.log("...{0}".format(self.events[i]), level=Monkey.DEBUG_LEVEL)
            except IndexError:
                self.log("...{0} has no events yet. Skipping.".format(calendar.day_name[i]), level="INFO")

        self.save()
        self.observations = []

    def schedule_today(self, kwargs):
        self.log("schedule_today({0})".format(kwargs), level=Monkey.DEBUG_LEVEL)

        today = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

        scheduled_events = 0
        skipped_events = 0
        for e in self.events[today.weekday()]:
            # TODO: add randomness
            time = e.dt.time()
            dt = datetime.datetime.combine(today.date(), time)
            if dt > datetime.datetime.now() + datetime.timedelta(seconds=5):
                h = self.run_at(self.monkey_do, dt, evnt=e)
                self.do_handles.append(h)
                self.log("scheduled event for {0}: {1}".format(dt, e), level="INFO")
                scheduled_events += 1
            else:
                skipped_events += 1
                self.log("event occurs in past, skipping ({0})...".format(time), level="INFO")

        self.log("{0} events for today, {1} scheduled, {2} skipped".format(len(self.events[today.weekday()]), scheduled_events, skipped_events), level="INFO")

    def forget(self, event_name, data, kwargs):
        self.log("forget({0}, {1}, {2})".format(event_name, data, kwargs), level=Monkey.DEBUG_LEVEL)

        self.events = {}
        for i in range(0, 7):
            self.events[i] = []

        self.save()

    def save(self):
        self.log(msg="save()", level=Monkey.DEBUG_LEVEL)

        self.log("saving {0} observations".format(self.len_d(self.events)), level="INFO")
        with open(self.events_db + '.pkl', 'wb') as f:
            pickle.dump(self.events, f, pickle.HIGHEST_PROTOCOL)

    def load(self, name):
        self.log(msg="load({0})".format(name), level=Monkey.DEBUG_LEVEL)

        self.log("loading observations", level="INFO")
        try:
            with open(name + '.pkl', 'rb') as f:
                self.log("loaded", level=Monkey.DEBUG_LEVEL)
                return pickle.load(f)
        except FileNotFoundError as fnfe:
            self.log("file not found: {0}".format(fnfe), level="WARN")
            return None
        except EOFError as eofe:
            self.log("error opening file: {0}".format(eofe), level="ERROR")
            return None


    @staticmethod
    def len_d(d):
        return sum([len(d[k]) for k in d.keys()])

    def terminate(self):
        self.log("terminate()", level=Monkey.DEBUG_LEVEL)

        self.remember()
