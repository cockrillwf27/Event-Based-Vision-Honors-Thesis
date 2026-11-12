import numpy as np
import csv

# ====================== USER SETTINGS ======================
SAMPLE_RATE = 100          # samples per second
OUTPUT_FILE = "meter_trial.csv"

# Updated segment table (sync flashes handled by 33500B Sync/Marker output, not in CSV)
segments = [
    # Zero hold
    {"type": "hold", "duration": 5.0, "voltage": 0.0},

    # Calibration holds ascending
    {"type": "hold", "duration": 5.0, "voltage": 1.0},
    {"type": "hold", "duration": 5.0, "voltage": 2.5},
    {"type": "hold", "duration": 5.0, "voltage": 4.0},
    {"type": "hold", "duration": 5.0, "voltage": 5.5},
    {"type": "hold", "duration": 5.0, "voltage": 7.0},
    {"type": "hold", "duration": 5.0, "voltage": 8.5},

    # Calibration holds descending (static hysteresis)
    {"type": "hold", "duration": 5.0, "voltage": 7.0},
    {"type": "hold", "duration": 5.0, "voltage": 5.5},
    {"type": "hold", "duration": 5.0, "voltage": 4.0},
    {"type": "hold", "duration": 5.0, "voltage": 2.5},
    {"type": "hold", "duration": 5.0, "voltage": 1.0},

    # Medium and large steps
    {"type": "step", "duration": 6.0, "v_start": 1.0, "v_end": 3.0},
    {"type": "step", "duration": 6.0, "v_start": 3.0, "v_end": 1.0},
    {"type": "step", "duration": 6.0, "v_start": 1.0, "v_end": 4.5},
    {"type": "step", "duration": 6.0, "v_start": 4.5, "v_end": 8.0},
    {"type": "step", "duration": 6.0, "v_start": 8.0, "v_end": 4.5},
    {"type": "step", "duration": 6.0, "v_start": 4.5, "v_end": 1.0},
    {"type": "step", "duration": 8.0, "v_start": 1.0, "v_end": 7.5},
    {"type": "step", "duration": 8.0, "v_start": 7.5, "v_end": 1.0},

    # Setup to mid-scale
    {"type": "step", "duration": 8.0, "v_start": 1.0, "v_end": 5.0},

    # Small steps around mid-scale
    {"type": "step", "duration": 4.0, "v_start": 5.0, "v_end": 5.1},
    {"type": "step", "duration": 4.0, "v_start": 5.1, "v_end": 5.35},
    {"type": "step", "duration": 4.0, "v_start": 5.35, "v_end": 5.85},
    {"type": "step", "duration": 4.0, "v_start": 5.85, "v_end": 5.35},
    {"type": "step", "duration": 4.0, "v_start": 5.35, "v_end": 5.1},
    {"type": "step", "duration": 4.0, "v_start": 5.1, "v_end": 5.0},

    # Setup to ramp start
    {"type": "step", "duration": 8.0, "v_start": 5.0, "v_end": 1.0},

    # Slow ramps
    {"type": "ramp", "duration": 40.0, "v_start": 1.0, "v_end": 8.5},
    {"type": "ramp", "duration": 40.0, "v_start": 8.5, "v_end": 1.0},

    # Medium ramps
    {"type": "ramp", "duration": 15.0, "v_start": 1.0, "v_end": 8.5},
    {"type": "ramp", "duration": 15.0, "v_start": 8.5, "v_end": 1.0},

    # Setup to sine center
    {"type": "step", "duration": 8.0, "v_start": 1.0, "v_end": 4.75},

    # Sines (4.75 V ± 2.5 V)
    {"type": "sine", "duration": 40.0, "amplitude": 2.5, "offset": 4.75, "frequency": 0.05},
    {"type": "sine", "duration": 30.0, "amplitude": 2.5, "offset": 4.75, "frequency": 0.1},
    {"type": "sine", "duration": 25.0, "amplitude": 2.5, "offset": 4.75, "frequency": 0.2},
    {"type": "sine", "duration": 20.0, "amplitude": 2.5, "offset": 4.75, "frequency": 0.5},
    {"type": "sine", "duration": 15.0, "amplitude": 2.5, "offset": 4.75, "frequency": 1.0},
    {"type": "sine", "duration": 10.0, "amplitude": 2.5, "offset": 4.75, "frequency": 2.0},

    # Rest periods
    {"type": "hold", "duration": 45.0, "voltage": 5.0},
    {"type": "hold", "duration": 30.0, "voltage": 1.0},

    # Final zero hold
    {"type": "hold", "duration": 5.0, "voltage": 0.0},
]
# ===========================================================

def generate_segment(seg, sample_rate):
    n = int(round(seg["duration"] * sample_rate))
    if n < 1:
        n = 1
    t = np.linspace(0, seg["duration"], n, endpoint=False)

    if seg["type"] == "hold":
        return np.full(n, seg["voltage"])

    elif seg["type"] == "step":
        # Instantaneous jump to v_end, then hold for the duration
        return np.full(n, seg["v_end"])

    elif seg["type"] == "ramp":
        return np.linspace(seg["v_start"], seg["v_end"], n)

    elif seg["type"] == "sine":
        return seg["offset"] + seg["amplitude"] * np.sin(2 * np.pi * seg["frequency"] * t)

    else:
        raise ValueError(f"Unknown segment type: {seg['type']}")

# Build full waveform
waveform = np.concatenate([generate_segment(s, SAMPLE_RATE) for s in segments])

# Write CSV (one voltage per line)
with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    for v in waveform:
        writer.writerow([f"{v:.6f}"])

total_samples = len(waveform)
total_time = total_samples / SAMPLE_RATE
print(f"Wrote {total_samples} samples ({total_time:.1f} s) to {OUTPUT_FILE}")
print(f"Voltage range: {waveform.min():.3f} V to {waveform.max():.3f} V")
print(f"End marker suggestion: place near sample {total_samples - 50} (last ~0.5 s)")
print("Set 33500B arb sample rate to", SAMPLE_RATE, "Sa/s and load to High Z after import.")
