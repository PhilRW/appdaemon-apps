# Lock Manager

This app manages lock codes behind the scenes. You will also need to add the various required entities and to configure the frontend to display the various entities.

## Sample apps.yaml config

```yaml
lock_manager:
  module: lock
  class: Manager
  codes: 4
  locks:
    - identifier: front
      lock: lock.front_door_lock
      alarm_level: sensor.front_door_lock_alarm_level
      alarm_type: sensor.front_door_lock_alarm_type
```

The app will warn you if it cannot find the required entities.

## Sample package config

Here's an example YAML file from the packages directory (copy and modify for each additional user code):

```yaml
input_text:
  lock_user_name_1:
    name: Name
  lock_user_pin_1:
    name: Code
    pattern: '^[0-9]{4,8}$'
    mode: password

input_select:
  lock_user_access_schedule_1_front:
    name: Front Door Access Schedule
    options:
      - Always
      - Recurring
      - Temporary
      - One-Time
      - Never
      - Manual

input_datetime:
  lock_user_start_dt_1_front:
    name: Front Door Start Date/Time
    has_date: true
    has_time: true
  lock_user_stop_dt_1_front:
    name: Front Door End Date/Time
    has_date: true
    has_time: true
  lock_user_start_time_1_front:
    name: Front Door Start Time
    has_time: true
  lock_user_stop_time_1_front:
    name: Front Door End Time
    has_time: true

input_boolean:
  lock_user_access_1_front:
    name: Front Door Access
```

## Sample ui-lovelace.yaml config

And here's an example Lovelace frontend configuration:

```yaml
  - title: Locks
    icon: mdi:lock-smart
    id: locks
    cards:
      - type: vertical-stack
        id: locks-user-1
        cards:
          - type: entities
            id: locks-user-entities-1
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
                state: "Recurring"
            card:
              type: entities
              id: locks-user-1-front-recurring-entities
              title: User 1 Front Door Recurring Access
              entities:
                - input_datetime.lock_user_start_time_1_front
                - input_datetime.lock_user_stop_time_1_front
          - type: conditional
            id: locks-user-1-front-temporary
            conditions:
              - entity: input_select.lock_user_access_schedule_1_front
                state: "Temporary"
            card:
              type: entities
              id: locks-user-1-front-temporary-entities
              title: User 1 Front Door Temporary Access
              entities:
                - input_datetime.lock_user_start_dt_1_front
                - input_datetime.lock_user_stop_dt_1_front
          - type: conditional
            id: locks-user-1-front-recurring
            conditions:
              - entity: input_select.lock_user_access_schedule_1_front
                state: "Manual"
            card:
              type: entities
              id: locks-user-1-front-manual-entities
              title: User 1 Front Door Manual Access
              show_header_toggle: false
              entities:
                - input_boolean.lock_user_access_1_front

```

