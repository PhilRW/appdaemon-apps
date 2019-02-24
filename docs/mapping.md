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

# Daily Color Name

This app is designed to set a state to a color name based on conditions. For example, if the weather forecast is cloudy, that can be mapped to a color name and assigned to a state variable.

## Sample config

```yaml
wake_up_color:
  module: mapping
  class: DailyColorName
  entity_id: input_text.wake_up_color_name
  default_color_names:
    - goldenrod
  rules:
    - name: My Birthday
      type: dom
      month: 1
      day: 1
      color_name: blue
    - name: Snowy day
      type: eval
      eval: self.entities.weather.dark_sky.attributes.forecast[0]["condition"]
      values:
        - snowy
      color_name: snow
    - name: Rainy day
      type: eval
      eval: self.entities.weather.dark_sky.attributes.forecast[0]["condition"]
      values:
        - rainy
        - snowy-rainy
      color_name: slateblue
    - name: Stormy day
      type: eval
      eval: self.entities.weather.dark_sky.attributes.forecast[0]["condition"]
      values:
        - hail
        - lightning
      color_name: orangered

```

