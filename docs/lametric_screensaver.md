# LaMetric Screensaver

Right now this works on the local network using a static IP to enable/disable the LaMetric screensaver functionality based on HA events. This is because where my LaMetric is located doesn't get enough light during the day to allow the automatic screensaver functionality (based on brightness) to work properly, but I still want to put it to "sleep" at night.

## Sample config

```yaml
lametric_sleep:
  module: LaMetric
  class: ScreensaverController
  device_ip: 192.168.1.123
  api_key: [redacted]
  sleep_event: LAMETRIC_SLEEP
  wake_event: LAMETRIC_WAKE
```

## Known issues

- [ ] Needs to determine IP of local LaMetric on its own (SSDP discovery perhaps?)