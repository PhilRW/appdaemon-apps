# Humidity Fan Controller

This app will turn on a switch when a relative humidty sensor reports over a certain threshold and will turn it off when it reports under a different, lower threshold.

## Sample config

Here is a sample `app.yaml` configuration:

``` yaml
bathroom_humidity_fan:
  module: FanController
  class: HumidityFan
  constrain_input_boolean: input_boolean.manual_override,off
  exhaust_fan: switch.bathroom_exhaust_fan
  humidity_sensor: sensor.bathroom_humidity
  motion_sensor: binary_sensor.bathroom_motion
  motion_sensor_timeout: 30
  rh_max: 80
  rh_target: 60
```

The only required parameters are `exhaust_fan` and `humidity_sensor`. The fan will start running when the relative humidity passes the upper level `rh_max` and will continue to run until it gets below the target threshold `rh_target`. If you supply `motion_sensor`, the fan will not activate until `motion_sensor_timeout` (in seconds) after the motion stops. You can also supply a `backup_fan` switch that will ignore the motion sensor setting. (My use case: turn on the furnace blower fan as a backup while leaving the bathroom exhaust fan sensitive to motion events.)

A simple on/off relative to humidity thresholds could be done fairly easily with conventional automations in Home Assistant, *however* if a user does not like the noise of the exhaust fan, things become more complicated and hence this app.

## Default values

You can override these parameters by supplying them as in the example above. Otherwise these are the defaults:

| parameter             | value |
| --------------------- | ----- |
| rh_max                | 60    |
| rh_target             | 50    |
| motion_sensor_timeout | 60    |