# Demos

Early proof-of-concept and camera bring-up scripts. These were used while getting the RGB baseline (Arducam UC-517 / IMX477) and event-camera (GenX320) hardware working on the Jetson Orin Nano. They are kept for reference, regression testing, and quick experiments.

## Scripts

| Script              | Purpose                                      | Notes |
|---------------------|----------------------------------------------|-------|
| `clock_poc.py`      | Early clock-hand / analog gauge proof of concept | RGB baseline precursor to the full benchmark clock reader |
| `dual_camera.py`    | Dual-camera capture experiments              | Used while testing multiple CSI cameras or mixed RGB + event setups |
| `Face_detect.py`    | Simple face-detection test                   | Quick OpenCV-style sanity check on the camera stream |
| `simple_camera.py`  | Minimal camera capture and display           | Lowest-level “does the camera work?” script |
| `test_camera.py`    | Basic camera functionality test              | General bring-up and debugging |

## Requirements

- Jetson Orin Nano with working CSI camera overlay (IMX477 for RGB scripts)
- OpenCV (`python3-opencv` or equivalent)
- For any GenX320-related tests: OpenEB / Metavision libraries already built and installed

## How to run

Most scripts are standalone. From this directory:

```bash
python3 simple_camera.py
python3 test_camera.py
python3 clock_poc.py
python3 dual_camera.py
python3 Face_detect.py
