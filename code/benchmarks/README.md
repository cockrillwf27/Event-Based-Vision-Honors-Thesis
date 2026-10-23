# Benchmarks
Scripts for comparing RGB and event-camera pipelines on the analog-gauge / clock-hand task.

## Metrics
- Pipeline latency
- Network latency
- End-to-end latency
- Clock-hand reading error
- Sensor bytes vs packet bytes
- Power (measured separately via battery-runtime trials, not a software sensor)

## Layout
- `protocol.py` – Shared protocol / message definitions
- `jetson/` – Scripts that run on the Jetson Orin Nano
- `host/` – Scripts that run on the computer (receiver / GUI side)

## How to run
See the README inside `jetson/` and `host/` for concrete commands and expected outputs.
