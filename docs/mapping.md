# Temperature-to-Hue Mapping

This app sets the state of an arbitrary sensor to a hue (0-360) according to a temperature sensor.

## Sample config

```yaml
temperature_to_hue:
  module: mapping
  class: TempToHue
  temperature_sensor: sensor.temperature
  low_temp: 0
  high_temp: 40
  output_entity: sensor.temperature_hue

```

