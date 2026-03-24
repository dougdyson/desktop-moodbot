# Battery Drain Test Results

## Test Setup

- **Date**: 2026-03-23 to 2026-03-24
- **Firmware**: v1.1.0 (all units)
- **Server**: `--no-sleep` mode (never sends sleeping=true)
- **Logging**: `MOODBOT_BATTERY_LOG=battery-test.log`
- **Server host**: 192.168.0.35:9400
- **Endpoint**: `GET /mood/claude-code`

## Units

| Unit | Serial | Poll interval |
|------|--------|---------------|
| A | 5B1F0105601 | 30s |
| B | 5A6D0098071 | 60s |
| C | 5A6C0814201 | 120s |
| D | 5A6D0043971 | 240s |

## Results

| Unit | Poll | Start V | End V | Drained | Runtime | Total polls |
|------|------|---------|-------|---------|---------|-------------|
| A | 30s | 3.50V | 2.35V | 1.15V | 8.7 hrs | 1,040 |
| B | 60s | 3.45V | 2.35V | 1.10V | 8.6 hrs | 514 |
| C | 120s | 3.49V | 2.28V | 1.21V | 9.8 hrs | 292 |
| D | 240s | 3.52V | 2.47V | 1.05V | 9.5 hrs | 142 |

## Conclusions

- Polling interval has minimal impact on battery life (~8.5-10 hrs across all intervals)
- ESP32 baseline power draw between polls dominates total consumption
- WiFi wake/poll/sleep cycle is a small fraction of total energy use
- 30s polling is viable for best responsiveness with negligible battery penalty
- Full charge voltage varies by unit (3.45-3.52V) due to TP4057 charger IC tolerances (true full LiPo = 4.2V)

## Notes

- Units do not reach full 4.2V LiPo charge — TP4057 charger IC cuts off early
- Deep sleep with button wake enabled on all units
- Server ran with `--no-sleep` to prevent units from entering deep sleep (which would extend battery life significantly in normal use)
