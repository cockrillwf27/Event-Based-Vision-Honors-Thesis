# Jetson-side benchmark scripts

## Files
- `clock_reader.py` – Clock-hand / gauge reading logic (RGB baseline)
- `rgb_sender.py` – Sends frames or results from the Jetson

## Setup notes
- Requires the IMX477 / Arducam UC-517 to be working with the appropriate CSI overlay.
- Runs on Jetson Orin Nano (hostname typically `orin-desktop`, user `orin`).

## Example usage
```bash
# (adjust paths and arguments as needed)
python3 clock_reader.py
python3 rgb_sender.py
