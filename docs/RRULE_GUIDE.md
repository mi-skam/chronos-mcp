# Recurring Events (RRULE) Support

Chronos MCP now supports recurring events using the RRULE standard (RFC 5545). This allows you to create events that repeat on a regular schedule.

## Quick Start

To create a recurring event, simply add the `recurrence_rule` parameter when creating an event:

```python
# Daily standup on weekdays
create_event(
    calendar_uid="work-calendar",
    summary="Daily Standup",
    start="2025-07-07T09:00:00",
    end="2025-07-07T09:30:00",
    recurrence_rule="FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR"
)

# Weekly team meeting
create_event(
    calendar_uid="team-calendar",
    summary="Team Meeting",
    start="2025-07-08T14:00:00",
    end="2025-07-08T15:00:00",
    recurrence_rule="FREQ=WEEKLY;BYDAY=TU"
)
```

## Supported RRULE Patterns

### Daily Recurrence
- `FREQ=DAILY` - Every day
- `FREQ=DAILY;INTERVAL=2` - Every other day
- `FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR` - Weekdays only
- `FREQ=DAILY;COUNT=10` - Daily for 10 occurrences
- `FREQ=DAILY;UNTIL=20251231T235959Z` - Daily until end of year

### Weekly Recurrence
- `FREQ=WEEKLY` - Every week
- `FREQ=WEEKLY;INTERVAL=2` - Every other week
- `FREQ=WEEKLY;BYDAY=MO,WE,FR` - Every Monday, Wednesday, Friday
- `FREQ=WEEKLY;BYDAY=SA,SU` - Weekends only

### Monthly Recurrence
- `FREQ=MONTHLY` - Same day each month
- `FREQ=MONTHLY;BYMONTHDAY=15` - 15th of each month
- `FREQ=MONTHLY;BYMONTHDAY=-1` - Last day of each month
- `FREQ=MONTHLY;BYDAY=2MO` - 2nd Monday of each month
- `FREQ=MONTHLY;BYDAY=-1FR` - Last Friday of each month
- `FREQ=MONTHLY;INTERVAL=3` - Quarterly (every 3 months)

### Yearly Recurrence
- `FREQ=YEARLY` - Anniversary of start date
- `FREQ=YEARLY;BYMONTH=3;BYMONTHDAY=15` - March 15th each year
- `FREQ=YEARLY;BYMONTH=12;BYMONTHDAY=25` - Christmas
- `FREQ=YEARLY;BYDAY=1MO;BYMONTH=9` - Labor Day (1st Monday in September)
- `FREQ=YEARLY;INTERVAL=2` - Every other year

## RRULE Components

### Required Component
- **FREQ**: Frequency of recurrence (DAILY, WEEKLY, MONTHLY, YEARLY)

### Optional Components
- **INTERVAL**: How often to repeat (default: 1)
- **COUNT**: Total number of occurrences
- **UNTIL**: End date/time for recurrence (YYYYMMDDTHHMMSSZ format)
- **BYDAY**: Days of week (MO, TU, WE, TH, FR, SA, SU)
  - Can include position for monthly: 2MO (2nd Monday), -1FR (last Friday)
- **BYMONTHDAY**: Day of month (1-31, or -1 for last day)
- **BYMONTH**: Month number (1-12)

## Validation Rules

Chronos MCP validates RRULE syntax before creating events:

1. **FREQ is required** - Every RRULE must start with FREQ=
2. **Valid FREQ values** - Only DAILY, WEEKLY, MONTHLY, YEARLY are supported
3. **Positive integers** - INTERVAL and COUNT must be positive integers
4. **Valid day codes** - BYDAY must use standard day abbreviations
5. **Date format** - UNTIL must be in YYYYMMDD or YYYYMMDDTHHMMSSZ format

## Examples

### Meeting Room Booking (Every Tuesday and Thursday)
```python
create_event(
    calendar_uid="facilities",
    summary="Conference Room A Reserved",
    start="2025-07-08T13:00:00",
    end="2025-07-08T14:00:00",
    recurrence_rule="FREQ=WEEKLY;BYDAY=TU,TH;UNTIL=20251231T235959Z"
)
```

### Monthly Reports (Last Friday of each month)
```python
create_event(
    calendar_uid="deadlines",
    summary="Monthly Report Due",
    start="2025-07-25T17:00:00",
    end="2025-07-25T17:30:00",
    recurrence_rule="FREQ=MONTHLY;BYDAY=-1FR"
)
```

### Quarterly Reviews (Every 3 months on the 15th)
```python
create_event(
    calendar_uid="management",
    summary="Quarterly Performance Review",
    start="2025-07-15T10:00:00",
    end="2025-07-15T11:00:00",
    recurrence_rule="FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=15"
)
```

## Error Handling

If an invalid RRULE is provided, Chronos MCP will return an error:

```python
# This will fail - FREQ is required
create_event(..., recurrence_rule="BYDAY=MO")
# Error: Invalid RRULE: RRULE must start with FREQ=

# This will fail - invalid frequency
create_event(..., recurrence_rule="FREQ=HOURLY")
# Error: Invalid RRULE: Invalid FREQ value: HOURLY

# This will fail - invalid day code
create_event(..., recurrence_rule="FREQ=WEEKLY;BYDAY=MONDAY")
# Error: Invalid RRULE: Invalid day abbreviation: MONDAY
```

## Limitations

- Only supports DAILY, WEEKLY, MONTHLY, and YEARLY frequencies
- Does not support HOURLY, MINUTELY, or SECONDLY frequencies
- Complex patterns with multiple BYMONTH or BYSETPOS are not validated
- Exception dates (EXDATE) are not yet supported
- Modification of recurring event instances not yet implemented

## Future Enhancements

- Support for modifying individual occurrences
- Exception dates (EXDATE) for skipping specific occurrences
- More complex recurrence patterns
- Timezone-aware UNTIL dates
