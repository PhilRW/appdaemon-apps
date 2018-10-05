# Monkey See, Monkey Do

Simulating presence while away is an important security feature of any good home automation system. While it is possible to manually program all the events that need to take place while a home is unoccupied, it would be easier on the user for the home to watch and learn while the home _is_ occupied and to replay those events when it is *not*.

This app does that. It watches the devices in the `entities` list for events and will replay them when you are away. Its memory is based on the day of the week and time of the event. It will fill in the gaps in its memory as it observes during "home" mode. Occupancy is determined by the `occupancy_state` parameter, which should be a binary_sensor that is on when occupied.

For best results, run this app for at least a week of occupancy. When you are away, it will do what you (or the automation system) would have done had you been home on that day of the week.

**NOTE**: If it did not observe you during that particular timeframe, it will not know what to do, so it will do nothing.

## Sample config

```yaml
monkey_see_monkey_do:
  module: ape
  class: Monkey
  occupancy_state: binary_sensor.occupancy
  forget_event: MONKEY_FORGET
  exit_delay: 300
  events_db: /share/ape
  entities:
    - light.bedroom_light
    - light.living_room_light
    - light.kitchen_light
    - switch.basement_light
```

`forget_event` is optional and will wipe its memory (database file) when you fire that event.

`exit_delay` is optional and lets you tweak the delay from when the `occupancy_state` sensor turns to `off` and when the app starts replaying events. This is useful for automation events that trigger after you depart, such as turning off lights. The default value is 60 (seconds).

`events_db` is optional and lets you customize the events database file. This is necessary if you are running more than once instance of the app. The default value is `/share/Monkey_events`. The extension `.pkl` is added to the filename, so do not specify that in the value.

## Known issues

- [ ] Needs some randomness to it
- [ ] Should be more flexible than looking at a single `binary_sensor` to determine occupancy
- [x] What if your automations turn off lights for you when you depart? Will it pick those up?