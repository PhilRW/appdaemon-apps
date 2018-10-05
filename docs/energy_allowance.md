# Energy Allowance

This simple app turns off an entity after a certain amount of time. If not specified, the timeout defaults to 600 seconds.

## Sample config

```yaml
energy_allowance_closet_light:
  module: energy
  class: Allowance
  entity: switch.closet_light
  timeout: 300
```

`timeout` is optional and is the number of seconds to allow the entity to stay on.