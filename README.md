# Personal AppDaemon Apps

These are my own personal [AppDaemon](http://appdaemon.readthedocs.io/en/stable/) apps for [Home Assistant](https://home-assistant.io/). I hope they are useful for you.

Use them at your own peril.

You can install them all by simply cloning this repo from within your AppDaemon `app_dir` directory. You may want to rename it. e.g.:

``` bash
cd /config/appdaemon/apps/
git clone git@github.com:PhilRW/appdaemon-apps.git philrw-apps
```

------

## Humidity Fan Controller

This app will turn on a switch when a relative humidty sensor reports over a certain threshold and will turn it off when it reports under a different, lower threshold.

### Sample config

Here is a sample `app.yaml` configuration:

``` yaml
bathroom_humidity_fan:
  module: FanController
  class: HumidityFan
  constrain_input_boolean: switch.manual_override,off
  exhaust_fan: switch.bathroom_exhaust_fan
  humidity_sensor: sensor.bathroom_humidity
  motion_sensor: binary_sensor.bathroom_motion
  motion_sensor_timeout: 30
  rh_max: 80
  rh_target: 60
```

The only required parameters are `exhaust_fan` and `humidity_sensor`. The fan will start running when the relative humidity passes the upper level `rh_max` and will continue to run until it gets below the target threshold `rh_target`. If you supply `motion_sensor`, the fan will not activate until `motion_sensor_timeout` (in seconds) after the motion stops. You can also supply a `backup_fan` switch that will ignore the motion sensor setting. (My use case: turn on the furnace blower fan as a backup while leaving the bathroom exhaust fan sensitive to motion events.)

A simple on/off relative to humidity thresholds could be done fairly easily with conventional automations in Home Assistant, *however* if a user does not like the noise of the exhaust fan, things become more complicated and hence this app.

### Default values

You can override these parameters by supplying them as in the example above. Otherwise these are the defaults:

| parameter             | value |
| --------------------- | ----- |
| rh_max                | 60    |
| rh_target             | 50    |
| motion_sensor_timeout | 60    |

------

## LaMetric Energy App

If you have a [LaMetric](https://lametric.com/) device and a [home energy meter](https://aeotec.com/z-wave-home-energy-measure) of some kind, you can create a near-realtime display of your power and energy usage, a power graph, and the time-of-use (TOU) metering rate that is currently active.

It is also useful for net metering customers who may have rooftop photovoltaic arrays (solar panels) or other local generation capabilities and would like to know if they are consuming or generating power without having to open an app or a webpage.

### Sample config

This app is hardcoded for my specific configuration and electricity provider but if there is enough interest it can be made more configurable. As it stands now I will provide the code as-is and leave the configuration example here:

```yaml
superior_lametric_hem:
  module: LaMetric
  class: EnergyApp
  lametric_app_id: [redacted]
  lametric_access_token: [redacted]
  power_meter: sensor.whole_house_power
  energy_meter: sensor.whole_house_energy
  energy_offset: 1234.567
```

`energy_offset` will add that value to the meter's energy (kWh) reading. This is in case you reset the meter on the device, inadvertently or otherwise, and would like to restore your previous reading.

### Known issues

- Same caveats as any service that is cloud-hosted: no internet = no work.

------

## LaMetric Screensaver

Right now this works on the local network using a static IP to enable/disable the LaMetric screensaver functionality based on HA events. This is because where my LaMetric is located doesn't get enough light during the day to allow the automatic screensaver functionality (based on brightness) to work properly, but I still want to put it to "sleep" at night.

### Sample config

```yaml
lametric_sleep:
  module: LaMetric
  class: ScreensaverController
  device_ip: 192.168.1.123
  api_key: [redacted]
  sleep_event: LAMETRIC_SLEEP
  wake_event: LAMETRIC_WAKE
```

### Known issues

- [ ] Needs to determine IP of local LaMetric on its own (SSDP discovery perhaps?)


------

## Monkey See, Monkey Do

Simulating presence while away is an important security feature of any good home automation system. While it is possible to manually program all the events that need to take place while a home is unoccupied, it would be easier on the user for the home to watch and learn while the home _is_ occupied and to replay those events when it is *not*.

This app does that. It watches the devices in the `entities` list for events and will replay them when you are away. Its memory is based on the day of the week and time of the event. It will fill in the gaps in its memory as it observes during "home" mode. Occupancy is determined by the `occupancy_state` parameter, which should be a binary_sensor that is on when occupied.

For best results, run this app for at least a week of occupancy. When you are away, it will do what you (or the automation system) would have done had you been home on that day of the week.

**NOTE**: If it did not observe you during that particular timeframe, it will not know what to do, so it will do nothing.

### Sample config

```yaml
monkey_see_monkey_do:
  module: ape
  class: Monkey
  occupancy_state: binary_sensor.occupancy
  forget_event: MONKEY_FORGET
  entities:
    - light.bedroom_light
    - light.living_room_light
    - light.kitchen_light
    - switch.basement_light
```

`forget_event` is optional and will wipe its memory (database file) when you fire that event.

### Known issues

- [ ] Needs some randomness to it
- [ ] Should be more flexible than looking at a single `binary_sensor` to determine occupancy
- [ ] What if your automations turn off lights for you when you depart? Will it pick those up?