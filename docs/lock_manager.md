# Lock Manager

This app manages lock codes behind the scenes. You will also need to add the various required entities and to configure the frontend to display the various entities.

## Sample apps.yaml config

```yaml
lock_manager:
  module: lock
  class: Manager
  packages_dir: /share/config/packages
  codes: 4
  locks:
    - identifier: front
      lock: lock.front_door_lock
      alarm_level: sensor.front_door_lock_alarm_level
      alarm_type: sensor.front_door_lock_alarm_type
```

The app will warn you if it cannot find the required entities and will attempt to automatically create them in the `packages_dir` directory (which should be writable by AppDaemon).

## Sample configuration.yaml config

It's also important to set the packages directory to the same as configured for the app.

```yaml
homeassistant:
  packages: !include_dir_named /share/config/packages
```

## Sample ui-lovelace.yaml config

And here's an example Lovelace frontend configuration:

```yaml
type: vertical-stack
id: locks-user-1
cards:
  - type: entities
    id: locks-user-1-entities
    title: User 1
    show_header_toggle: false
    entities:
      - input_text.lock_user_name_1
      - input_text.lock_user_pin_1
      - input_select.lock_user_access_schedule_1_front
  - type: conditional
    id: locks-user-1-front-recurring
    conditions:
      - entity: input_select.lock_user_access_schedule_1_front
        state: Recurring
    card:
      type: entities
      id: locks-user-1-front-recurring-entities
      title: User 1 Front Door Recurring Access
      show_header_toggle: false
      entities:
        - input_datetime.lock_user_start_time_1_front
        - input_datetime.lock_user_stop_time_1_front
  - type: conditional
    id: locks-user-1-front-temporary
    conditions:
      - entity: input_select.lock_user_access_schedule_1_front
        state: Temporary
    card:
      type: entities
      id: locks-user-1-front-temporary-entities
      title: User 1 Front Door Temporary Access
      show_header_toggle: false
      entities:
        - input_datetime.lock_user_start_dt_1_front
        - input_datetime.lock_user_stop_dt_1_front
  - type: conditional
    id: locks-user-1-front-manual
    conditions:
      - entity: input_select.lock_user_access_schedule_1_front
        state: Manual
    card:
      type: entities
      id: locks-user-1-front-manual-entities
      title: User 1 Front Door Manual Access
      show_header_toggle: false
      entities:
        - input_boolean.lock_user_access_1_front
```

