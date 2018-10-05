# Time Of Use (TOU)

This app sets the state of an arbitrary entity according to the current TOU rate. Currently it is set up for Xcel Energy in Colorado.

You can use the `device` in other apps or automations. The states are "on-peak", "shoulder", and "off-peak". There is also an attribute called "lametric_icon" that is a red, yellow, or green icon for the respective TOU states.

## Sample config

```yaml
tou_mode_manager:
  module: tou
  class: StateManagerXcelColorado
  device: input_select.tou_mode
```