# Button Translator

This app listens for button presses and determines a pattern. Presses shorter than `dash` ("-") in seconds are considered a *dot* ("."). If a match is found, the app will fire the corresponding event.

## Sample apps.yaml config

```yaml
button_1_listener:
  module: button
  class: Translator
  button: binary_sensor.button_1
  dash: 0.2
  timeout: 2
  events:
    ".": TOGGLE_HOME
    "...---...": SOS
```

`timeout` is the duration after releasing the button that the app consideres the sequence finished and will fire the event (if a match is found).