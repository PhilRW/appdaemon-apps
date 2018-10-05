# Todoist Tasks on Lametric

You can use this app to have your LaMetric device display tasks from a [Todoist](https://todoist.com/) project.

## Sample config

```yaml
lametric_tasks:
  module: LaMetric
  class: TaskApp
  lametric_app_id: [redacted]
  lametric_access_token: [redacted]
  device_ip: 192.168.1.100
  calendar: calendar.household_due_today
```

`device_ip` is optional and will use the local IP of the device to push updates. If omitted it will use the lametric developer server.