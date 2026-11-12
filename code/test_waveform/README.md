## Test Waveform

Controlled voltage sequence used to drive a Simpson 260 analog multimeter (fixed DC volts range) for the event-camera vs. RGB gauge-reading experiments.

### Purpose
Characterizes needle response so the event-camera results can be compared against a known ground-truth voltage:
- Accuracy and static hysteresis (ascending/descending calibration holds)
- Latency, settling, overshoot, and ringing (step responses)
- Tracking and dynamic hysteresis (slow and medium ramps)
- Frequency-response limit (sine segments at increasing frequency)
- Event rate and data volume when nothing is changing (rest periods)

### Segment Table
| Seg | Type       | Voltage / Frequency          | Duration | What it tests |
|-----|------------|------------------------------|----------|---------------|
| 1   | hold       | 0.0 V                        | 5 s      | Zero offset |
| 2   | hold ↑     | 1.0 V                        | 5 s      | Accuracy / calibration |
| 3   | hold ↑     | 2.5 V                        | 5 s      | Accuracy / calibration |
| 4   | hold ↑     | 4.0 V                        | 5 s      | Accuracy / calibration |
| 5   | hold ↑     | 5.5 V                        | 5 s      | Accuracy / calibration |
| 6   | hold ↑     | 7.0 V                        | 5 s      | Accuracy / calibration |
| 7   | hold ↑     | 8.5 V                        | 5 s      | Accuracy / calibration |
| 8   | hold ↓     | 7.0 V                        | 5 s      | Static hysteresis |
| 9   | hold ↓     | 5.5 V                        | 5 s      | Static hysteresis |
| 10  | hold ↓     | 4.0 V                        | 5 s      | Static hysteresis |
| 11  | hold ↓     | 2.5 V                        | 5 s      | Static hysteresis |
| 12  | hold ↓     | 1.0 V                        | 5 s      | Static hysteresis |
| 13  | step+hold  | 1.0 → 3.0 V                  | 6 s      | Latency / settling, medium up |
| 14  | step+hold  | 3.0 → 1.0 V                  | 6 s      | Latency / settling, medium down |
| 15  | step+hold  | 1.0 → 4.5 V                  | 6 s      | Latency / settling, large up |
| 16  | step+hold  | 4.5 → 8.0 V                  | 6 s      | Large up, upper scale |
| 17  | step+hold  | 8.0 → 4.5 V                  | 6 s      | Large down, upper scale |
| 18  | step+hold  | 4.5 → 1.0 V                  | 6 s      | Latency / settling, large down |
| 19  | step+hold  | 1.0 → 7.5 V                  | 8 s      | Full-swing up, overshoot / ringing |
| 20  | step+hold  | 7.5 → 1.0 V                  | 8 s      | Full-swing down, overshoot / ringing |
| 21  | step+hold  | 1.0 → 5.0 V                  | 8 s      | Move to mid-scale (settled) |
| 22  | small step | 5.0 → 5.1 V (+0.1)           | 4 s      | Smallest change that still produces events |
| 23  | small step | 5.1 → 5.35 V (+0.25)         | 4 s      | Small-step sensitivity |
| 24  | small step | 5.35 → 5.85 V (+0.5)         | 4 s      | Small-step sensitivity |
| 25  | small step | 5.85 → 5.35 V (−0.5)         | 4 s      | Small-step sensitivity, down |
| 26  | small step | 5.35 → 5.1 V (−0.25)         | 4 s      | Small-step sensitivity, down |
| 27  | small step | 5.1 → 5.0 V (−0.1)           | 4 s      | Smallest change that still produces events, down |
| 28  | step+hold  | 5.0 → 1.0 V                  | 8 s      | Move to ramp start |
| 29  | ramp       | 1.0 → 8.5 V (~0.19 V/s)      | 40 s     | Slow tracking |
| 30  | ramp       | 8.5 → 1.0 V                  | 40 s     | Dynamic hysteresis, reverse tracking |
| 31  | ramp       | 1.0 → 8.5 V (0.5 V/s)        | 15 s     | Faster tracking |
| 32  | ramp       | 8.5 → 1.0 V                  | 15 s     | Faster reverse tracking |
| 33  | step+hold  | 1.0 → 4.75 V                 | 8 s      | Move to sine center |
| 34  | sine       | 4.75 V ± 2.5 V, 0.05 Hz      | 40 s     | Low-frequency tracking |
| 35  | sine       | same, 0.1 Hz                 | 30 s     | Tracking |
| 36  | sine       | same, 0.2 Hz                 | 25 s     | Tracking |
| 37  | sine       | same, 0.5 Hz                 | 20 s     | Onset of lag / amplitude loss |
| 38  | sine       | same, 1.0 Hz                 | 15 s     | Frequency response limit |
| 39  | sine       | same, 2.0 Hz                 | 10 s     | Past the limit (optional) |
| 40  | hold       | 5.0 V                        | 45 s     | Event rate / data volume at rest, mid-scale |
| 41  | hold       | 1.0 V                        | 30 s     | Event rate at rest, low scale |
| 42  | hold       | 0.0 V                        | 5 s      | Zero return / end reference |

### Contents
- `build_meter_waveform.py` — generates the commanded-voltage CSV from the table above
- `meter_trial.csv` — one voltage sample per line, ready for import

### How to run a trial
1. Generate or copy `meter_trial.csv`.
2. On the Keysight 33500B:
   - Import the CSV as an arbitrary waveform
   - Set arb sample rate to **100 Sa/s**
   - Set output load to **High Z**
   - Enable Sync → Marker (sample 0 for start flash, near the end for end flash)
3. Drive an LED from the Sync BNC so both cameras see the flash.
4. Log timestamp, commanded voltage, measured terminal voltage, and the angles reported by the event camera and RGB camera.

All voltages stay inside the safe 0–8.5 V window on the 10 V DC range. Each measurement segment is long enough for the needle to settle. Sync flashes are generated optically from the 33500B Sync/Marker output and are not part of the CSV.
