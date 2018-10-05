# LaMetric Energy App

If you have a [LaMetric](https://lametric.com/) device and a [home energy meter](https://aeotec.com/z-wave-home-energy-measure) of some kind, you can create a near-realtime display of your power and energy usage, a power graph, and the time-of-use (TOU) metering rate that is currently active.

It is also useful for net metering customers who may have rooftop photovoltaic arrays (solar panels) or other local generation capabilities and would like to know if they are consuming or generating power without having to open an app or a webpage.

## Sample config

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
  dependencies: tou_mode_manager
  tou_mode: input_select.tou_mode
```

`energy_offset` will add that value to the meter's energy (kWh) reading. This is in case you reset the meter on the device, inadvertently or otherwise, and would like to restore your previous reading.

`dependencies` and `tou_mode` are optional and depend on the separate `tou` module.

## Known issues

- Same caveats as any service that is cloud-hosted: no internet = no work.