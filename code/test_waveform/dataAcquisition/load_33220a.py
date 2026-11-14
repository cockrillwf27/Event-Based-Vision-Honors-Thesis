#!/usr/bin/env python3
"""Load meter_trial.csv into Agilent 33220A (DATA VOLATILE, -1 to +1)."""
import pyvisa
import numpy as np
from pathlib import Path

CSV_FILE = Path("meter_trial.csv")
VISA_RESOURCE = "USB0::0x0957::0x0407::MY43005577::0::INSTR"
SAMPLE_RATE = 100  # Sa/s

def main():
    voltages = np.loadtxt(CSV_FILE)
    print(f"Loaded {len(voltages)} points")

    # Scale 0–8.5 V into the -1…+1 range the 33220A expects
    v_min, v_max = voltages.min(), voltages.max()
    if v_max == v_min:
        norm = np.zeros_like(voltages)
    else:
        norm = 2 * (voltages - v_min) / (v_max - v_min) - 1
    norm = np.clip(norm, -1, 1)

    rm = pyvisa.ResourceManager()
    inst = rm.open_resource(VISA_RESOURCE)
    inst.timeout = 60000
    inst.write("*CLS")
    print("Connected:", inst.query("*IDN?").strip())

    # Download in chunks if needed (33220A limit is 64k points)
    data_str = ",".join(f"{x:.6f}" for x in norm)
    inst.write(f"DATA VOLATILE, {data_str}")
    print("After DATA:", inst.query("SYST:ERR?").strip())

    inst.write("FUNC:USER VOLATILE")
    inst.write("FUNC USER")
    # Set amplitude and offset so the output matches the original voltages
    inst.write(f"VOLT {v_max - v_min}")
    inst.write(f"VOLT:OFFS {(v_max + v_min) / 2}")
    inst.write("OUTP:LOAD INF")
    inst.write("OUTP ON")
    print("After setup:", inst.query("SYST:ERR?").strip())
    print(f"Output range: {v_min:.3f} V to {v_max:.3f} V")
    inst.close()

if __name__ == "__main__":
    main()