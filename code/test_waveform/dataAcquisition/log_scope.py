#!/usr/bin/env python3
"""Pull a long waveform from a Keysight DSO-X 2012A and save reference_v.csv."""
import pyvisa
import numpy as np
from pathlib import Path

OUTPUT_CSV = Path("reference_v.csv")
CHANNEL = 1
TIMEBASE_S_DIV = 50

def main():
    rm = pyvisa.ResourceManager()
    resources = rm.list_resources()
    print("Available resources:")
    for i, r in enumerate(resources):
        print(f"  {i}: {r}")

    # Prefer Keysight USB (0x2A8D)
    keysight = [r for r in resources if "0x2A8D" in r]
    if not keysight:
        print("No Keysight scope found. Enter the number of the correct resource:")
        idx = int(input("Resource number: "))
        resource = resources[idx]
    else:
        resource = keysight[0]
        print(f"Using {resource}")

    scope = rm.open_resource(resource)
    scope.timeout = 120000
    scope.write("*CLS")
    print("Connected:", scope.query("*IDN?").strip())

    scope.write(f":CHAN{CHANNEL}:DISP ON")
    scope.write(f":CHAN{CHANNEL}:COUP DC")
    scope.write(f":CHAN{CHANNEL}:SCAL 2")
    scope.write(f":CHAN{CHANNEL}:OFFS 4")
    scope.write(f":TIM:SCAL {TIMEBASE_S_DIV}")
    scope.write(":TRIG:EDGE:SOUR CHAN1")
    scope.write(":TRIG:EDGE:LEV 1")
    scope.write(":TRIG:SWE NORM")

    input("Scope armed. Start the 33220A (with the Sync flash), then press Enter...")

    scope.write(":SING")
    scope.query("*OPC?")
    print("Acquisition complete. Downloading...")

    scope.write(f":WAV:SOUR CHAN{CHANNEL}")
    scope.write(":WAV:FORM ASCII")
    scope.write(":WAV:POIN:MODE RAW")
    preamble = scope.query(":WAV:PRE?").split(",")
    x_inc = float(preamble[4])
    x_orig = float(preamble[5])
    y_inc = float(preamble[7])
    y_orig = float(preamble[8])
    y_ref = float(preamble[9])

    raw = scope.query(":WAV:DATA?").strip()
    values = [float(x) for x in raw.replace("#", "").split(",") if x.strip()]
    voltage = np.array(values)
    if voltage.max() > 50:
        voltage = (voltage - y_ref) * y_inc + y_orig

    t = np.arange(len(voltage)) * x_inc + x_orig

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w") as f:
        f.write("t_ref_s,measured_v\n")
        for ti, vi in zip(t, voltage):
            f.write(f"{ti:.6f},{vi:.6f}\n")

    print(f"Wrote {len(voltage)} points to {OUTPUT_CSV}")
    scope.close()

if __name__ == "__main__":
    main()