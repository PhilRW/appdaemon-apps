import datetime
import os
import random
import re

import appdaemon.plugins.hass.hassapi as hass


class EntityType:

    def __init__(self, name, typ):
        self.name = name
        self.typ = typ


class Lock:

    def __init__(self, parent, identifier, lock, alarm_type, alarm_level):
        self.parent = parent
        self.identifier = identifier
        self.lock = lock
        self.alarm_type = alarm_type
        self.alarm_level = alarm_level

    def __repr__(self):
        return "Lock<{0}: {1}>".format(self.identifier, self.lock)

    def node_id(self):
        return int(self.parent.get_state(self.lock, attribute="node_id"))


ENTITY_PREFIX = "lock_user"

PIN = EntityType("pin", "input_text")
NAME = EntityType("name", "input_text")
SCHEDULE = EntityType("access_schedule", "input_select")
START_DT = EntityType("start_dt", "input_datetime")
STOP_DT = EntityType("stop_dt", "input_datetime")
START_TIME = EntityType("start_time", "input_datetime")
STOP_TIME = EntityType("stop_time", "input_datetime")
ACCESS = EntityType("access", "input_boolean")

SCHEDULE_ALWAYS = "Always"
SCHEDULE_RECURRING = "Recurring"
SCHEDULE_TEMPORARY = "Temporary"
SCHEDULE_ONETIME = "One-Time"
SCHEDULE_NEVER = "Never"
SCHEDULE_MANUAL = "Manual"


class Manager(hass.Hass):
    DEBUG_LEVEL = "DEBUG"

    def initialize(self):
        self.log("initialize()", level=Manager.DEBUG_LEVEL)
        self.log("args: {0}".format(self.args), level="INFO")

        if "packages_dir" and "codes" and "locks" not in self.args:
            self.log("Incorrect configuration.", level="WARNING")
            raise ValueError("Incorrect configuration.")

        self.codes = int(self.args['codes'])
        self.users = []
        self.locks = [Lock(self, l["identifier"], l["lock"], l["alarm_type"], l["alarm_level"]) for l in self.args["locks"]]
        self.keys_1 = [
            NAME,
            PIN
        ]
        self.keys_2 = [
            SCHEDULE,
            START_DT,
            STOP_DT,
            START_TIME,
            STOP_TIME,
            ACCESS
        ]

        for i in range(self.codes):
            pin_entity = self.get_entity(PIN, i + 1)
            name_entity = self.get_entity(NAME, i + 1)

            self.users.append((name_entity, pin_entity))

        self.log("users: {0}".format(self.users), level=Manager.DEBUG_LEVEL)
        self.log("locks: {0}".format(self.locks), level=Manager.DEBUG_LEVEL)

        if self.all_entities_exist():
            for i in range(self.codes):
                self.listen_state(self.pin_listener, self.get_entity(PIN, i + 1), code_id=i + 1)
            for l in self.locks:
                self.listen_state(self.lock_alarm_level_listener, l.alarm_level, lock=l)
                for i in range(self.codes):
                    self.run_minutely(self.set_access, None, code_id=i + 1, lock=l)
                    self.listen_state(self.set_code, self.get_entity(ACCESS, i + 1, l), new="on", code_id=i + 1, lock=l)
                    self.listen_state(self.clear_code, self.get_entity(ACCESS, i + 1, l), new="off", code_id=i + 1, lock=l)
                    self.listen_state(self.access_schedule_listener, self.get_entity(SCHEDULE, i + 1, l), code_id=i + 1, lock=l)
        else:
            self.log("Problem processing configuration, application halted.", level="WARNING")
            self.generate_config()

    def set_access(self, kwargs):
        self.log("set_access({0})".format(kwargs), level=Manager.DEBUG_LEVEL)

        code_id = kwargs['code_id']
        lock = kwargs["lock"]
        access_schedule = self.get_state(self.get_entity(SCHEDULE, code_id, lock))
        access_switch = self.get_entity(ACCESS, code_id, lock)
        manual_override = access_schedule == SCHEDULE_MANUAL or access_schedule == SCHEDULE_ONETIME
        access = False

        if not manual_override:
            if access_schedule == SCHEDULE_ALWAYS:
                access = True
            elif access_schedule == SCHEDULE_RECURRING:
                now = datetime.datetime.now()
                try:
                    start_time = int(self.get_state(self.get_entity(START_TIME, code_id, lock), attribute="timestamp"))
                    stop_time = int(self.get_state(self.get_entity(STOP_TIME, code_id, lock), attribute="timestamp"))
                    now = (((now.hour * 60) + now.minute) * 60) + now.second
                    if stop_time > start_time:
                        access = stop_time > now >= start_time
                    else:
                        access = not (start_time >= now > stop_time)
                except Exception as e:
                    self.log("Problem getting time from timestamp for code {0} on lock {1}: {2}".format(code_id, lock, e), level="ERROR")
            elif access_schedule == SCHEDULE_TEMPORARY:
                now = datetime.datetime.now()
                try:
                    start_dt = datetime.datetime.fromtimestamp(int(self.get_state(self.get_entity(START_DT, code_id, lock), attribute="timestamp")))
                    stop_dt = datetime.datetime.fromtimestamp(int(self.get_state(self.get_entity(STOP_DT, code_id, lock), attribute="timestamp")))
                    access = stop_dt > now > start_dt
                except Exception as e:
                    self.log("Problem getting datetime from timestamp for code {0} on lock {1}: {2}".format(code_id, lock, e), level="ERROR")
            elif access_schedule == SCHEDULE_NEVER:
                access = False

            if access:
                self.log("turning on {0}".format(access_switch), level=Manager.DEBUG_LEVEL)
                self.turn_on(access_switch)
            else:
                self.log("turning off {0}".format(access_switch), level=Manager.DEBUG_LEVEL)
                self.turn_off(access_switch)

    def get_entity(self, entity: EntityType, code_id: int, lock: Lock = None) -> str:
        self.log("get_entity({0}, {1}, {2})".format(entity, code_id, lock), level=Manager.DEBUG_LEVEL)

        if lock:
            ret = "{0}.{1}_{2}_{3}_{4}".format(entity.typ, ENTITY_PREFIX, entity.name, code_id, lock.identifier)
        else:
            ret = "{0}.{1}_{2}_{3}".format(entity.typ, ENTITY_PREFIX, entity.name, code_id)
        return ret

    def all_entities_exist(self) -> bool:
        self.log("all_entities_exist()", level=Manager.DEBUG_LEVEL)

        all_entities = self.get_state().keys()
        go_on = True
        for i in range(self.codes):
            for l in self.locks:
                for k in self.keys_1:
                    entity = self.get_entity(k, i + 1)
                    if entity not in all_entities:
                        self.log("{0} does not exist.".format(entity), level="ERROR")
                        go_on = False
                for k in self.keys_2:
                    entity = self.get_entity(k, i + 1, l)
                    if entity not in all_entities:
                        self.log("{0} does not exist.".format(entity), level="ERROR")
                        go_on = False
        return go_on

    def set_code(self, entity, attribute, old, new, kwargs):
        self.log("set_code({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=Manager.DEBUG_LEVEL)

        code_id = kwargs["code_id"]
        code = self.get_state(self.get_entity(PIN, code_id))
        lock = kwargs["lock"]

        pattern = re.compile("^[0-9]{4,8}$")
        if pattern.match(code) is not None:
            self.log("lock/set_usercode node_id={0} code_slot={1} usercode={2}".format(lock.node_id(), code_id, "*" * len(code)))
            self.call_service("lock/set_usercode", node_id=lock.node_id(), code_slot=code_id, usercode=code)
        else:
            self.log("Code is invalid, not sending.".format(code), level="WARNING")

    def clear_code(self, entity, attribute, old, new, kwargs):
        self.log("clear_code({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=Manager.DEBUG_LEVEL)

        code_id = kwargs["code_id"]
        lock = kwargs["lock"]

        self.log("lock/clear_usercode node_id={0} usercode={1}".format(lock.node_id(), code_id))
        self.call_service("lock/clear_usercode", node_id=lock.node_id(), code_slot=code_id)

    def lock_alarm_level_listener(self, entity, attribute, old, new, kwargs):
        self.log("lock_alarm_level_listener({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=Manager.DEBUG_LEVEL)

        lock = kwargs["lock"]
        alarm_type = int(self.get_state(lock.alarm_type))
        alarm_level = int(new)

        if alarm_type == 19:
            code_id = alarm_level
            user_name = self.get_state(self.get_entity(NAME, code_id))
            self.log("{0} unlocked by {1}.".format(lock.identifier.title(), user_name))

            access_schedule = self.get_entity(SCHEDULE, code_id, lock)
            if self.get_state(access_schedule) == SCHEDULE_ONETIME:
                self.log("Clearing code {0} from {1} lock after one-time use.".format(code_id, lock.identifier))
                self.call_service("input_select/select_option", entity_id=access_schedule, option=SCHEDULE_NEVER)
        elif alarm_type == 21:
            if alarm_level == 1:
                self.log("{0} manually locked.".format(lock.identifier.title()))
            elif alarm_level == 2:
                self.log("{0} locked by keypad.".format(lock.identifier.title()))
        elif alarm_type == 22:
            self.log("{0} manually unlocked.".format(lock.identifier.title()))
        elif alarm_type == 23:
            self.log("{0} remote lock jammed.".format(lock.identifier.title()))
        elif alarm_type == 24:
            self.log("{0} remotely locked.".format(lock.identifier.title()))
        elif alarm_type == 25:
            self.log("{0} remotely unlocked.".format(lock.identifier.title()))
        elif alarm_type == 26:
            self.log("{0} auto-relock jammed.".format(lock.identifier.title()))
        elif alarm_type == 27:
            self.log("{0} auto-relocked.".format(lock.identifier.title()))
        elif alarm_type == 32:
            self.log("{0} all codes deleted.".format(lock.identifier.title()))
        elif alarm_type == 122:
            self.log("{0} updated code {1}.".format(lock.identifier.title(), alarm_level))
        elif alarm_type == 161:
            self.log("{0} tampered!".format(lock.identifier.title()))
        elif alarm_type == 167:
            self.log("Low battery on {0}: REPLACE BATTERIES.".format(lock.identifier))
        elif alarm_type == 168:
            self.log("Critically low battery on {0}: REPLACE BATTERIES NOW!".format(lock.identifier))
        elif alarm_type == 169:
            self.log("Battery to low to operate {0}.".format(lock.identifier))
        else:
            self.log("Unknown alarm {0} level {1} on {2}.".format(alarm_type, alarm_level, lock.identifier))

    def access_schedule_listener(self, entity, attribute, old, new, kwargs):
        self.log("access_schedule_listener({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=Manager.DEBUG_LEVEL)

        code_id = kwargs["code_id"]
        lock = kwargs["lock"]

        self.set_access(kwargs)

        if new == SCHEDULE_ONETIME:
            input_pin = self.get_entity(PIN, code_id)
            random_pin = random.randint(1000, 9999)
            access_switch = self.get_entity(ACCESS, code_id, lock)

            self.log("input_text/set_value entity_id={0} value={1}".format(input_pin, random_pin))
            self.call_service("input_text/set_value", entity_id=input_pin, value=random_pin)
            self.set_state(input_pin, attributes={"mode": "text"})

            self.log("turning on {0}".format(access_switch), level=Manager.DEBUG_LEVEL)
            self.turn_on(access_switch)

    def pin_listener(self, entity, attribute, old, new, kwargs):
        self.log("pin_listener({0}, {1}, {2}, {3}, {4})".format(entity, attribute, old, new, kwargs), level=Manager.DEBUG_LEVEL)

        code_id = kwargs["code_id"]

        if new != old:
            self.log("Sending new PIN for code {0}.".format(code_id), level=Manager.DEBUG_LEVEL)

            for l in self.locks:
                kwargs["lock"] = l
                if self.get_state(self.get_entity(ACCESS, code_id, l)) == "on":
                    self.log("Access code {0} on lock {1} is enabled, re-sending.".format(code_id, l.identifier), Manager.DEBUG_LEVEL)
                    self.set_code(None, None, None, None, kwargs)

    def generate_config(self):
        self.log("generate_config()", level=Manager.DEBUG_LEVEL)

        for i in range(self.codes):
            package_out = """
input_text:

  {0}:
    name: Name
  {1}:
    name: Code
    pattern: '^[0-9]{{4,8}}$'
    mode: password

input_select:
""".format(self.get_entity(NAME, i + 1).split(".")[-1],
           self.get_entity(PIN, i + 1).split(".")[-1])

            for l in self.locks:
                package_out += """
  {0}:
    name: {1} Access Schedule
    options:
      - {2}
      - {3}
      - {4}
      - {5}
      - {6}
      - {7}
""".format(self.get_entity(SCHEDULE, i + 1, l).split(".")[-1],
           l.identifier.title(),
           SCHEDULE_ALWAYS,
           SCHEDULE_RECURRING,
           SCHEDULE_TEMPORARY,
           SCHEDULE_ONETIME,
           SCHEDULE_NEVER,
           SCHEDULE_MANUAL)

            package_out += """
input_datetime:
"""

            for l in self.locks:
                package_out += """
  {0}:
    name: {4} Start Date/Time
    has_date: true
    has_time: true
  {1}:
    name: {4} End Date/Time
    has_date: true
    has_time: true
  {2}:
    name: {4} Start Time
    has_time: true
  {3}:
    name: {4} End Time
    has_time: true
""".format(self.get_entity(START_DT, i + 1, l).split(".")[-1],
           self.get_entity(STOP_DT, i + 1, l).split(".")[-1],
           self.get_entity(START_TIME, i + 1, l).split(".")[-1],
           self.get_entity(STOP_TIME, i + 1, l).split(".")[-1],
           l.identifier.title())

            package_out += """
input_boolean:
"""

            for l in self.locks:
                package_out += """
  {0}:
    name: {1} Access
""".format(self.get_entity(ACCESS, i + 1, l).split(".")[-1],
           l.identifier.title())

            package_fn = os.path.join(self.args["packages_dir"], "{0}_{1}.yaml".format(ENTITY_PREFIX, i + 1))

            file = open(package_fn, "w")
            file.write(package_out)
            file.close()

        self.log("Automatic configuration re-generated in {0}. Please restart HA.".format(self.args["packages_dir"]))
