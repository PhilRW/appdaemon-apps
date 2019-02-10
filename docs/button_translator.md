# Button Translator

This app listens for button presses and determines a pattern. Presses shorter than `dash` ("-") in seconds are considered a *dot* ("."). If a match is found, the app will fire the corresponding event.

## Sample apps.yaml config

```yaml
button_1_listener:
  module: button
  class: Translator
  button: binary_sensor.button_1
  light_mode_event: TOGGLE_LIGHT_MORSE_CODE_MODE
  lights:
    - light.light_1
    - light.light_2
  dash: 0.2
  timeout: 2
  events:
    ".": TOGGLE_HOME
    "...---...": SOS
```

`timeout` is the duration after releasing the button that the app consideres the sequence finished and will fire the event (if a match is found).

`light_mode_event` and `lights` are optional but they will switch into a button controlled mode when `light_mode_event` is fired. You can also fire the `light_mode_event` with the button itself and it will serve to toggle the mode and ignore all other events when the mode is on.