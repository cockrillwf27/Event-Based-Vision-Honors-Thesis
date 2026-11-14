#!/usr/bin/env python3
"""Load Simpson 260 waveform, flash Sync LED, and start the trial on the 33220A."""
import pyvisa
import numpy as np
import time
from pathlib import Path

CSV_FILE = Path("meter_trial.csv")
VISA = "USB0::0x0957::0x0407::MY43005577::0::INSTR"

def main():
    voltages = np.loadtxt(CSV_FILE)
    n = len(voltages)
    v_min, v_max = float(voltages.min()), float(voltages.max())
    print(f"Points: {n}, range {v_min:.2f}–{v_max:.2f} V")

    # Normalize to -1…+1
    norm = 2 * (voltages - v_min) / (v_max - v_min) - 1
    norm = np.clip(norm, -1, 1)

    rm = pyvisa.ResourceManager()
    inst = rm.open_resource(VISA)
    inst.timeout = 60000
    inst.write("*CLS")
    print("Connected:", inst.query("*IDN?").strip())

    # Download waveform
    data_str = ",".join(f"{x:.5f}" for x in norm)
    inst.write(f"DATA VOLATILE, {data_str}")
    print("DATA:", inst.query("SYST:ERR?").strip())

    # Select arb and set amplitude/offset
    inst.write("FUNC:USER VOLATILE")
    inst.write("FUNC USER")
    inst.write("OUTP:LOAD INF")
    inst.write("VOLT:OFFS 0")
    inst.write(f"VOLT {v_max - v_min}")
    inst.write(f"VOLT:OFFS {(v_max + v_min)/2}")
    print("AMP/OFFS:", inst.query("SYST:ERR?").strip())

    # Set slow frequency (100 Sa/s design rate)
    total_time = n / 100.0
    freq = 1.0 / total_time
    inst.write(f"FREQ {freq:.8f}")
    print(f"Frequency: {freq:.6f} Hz ({total_time:.0f} s)")
    print("FREQ:", inst.query("SYST:ERR?").strip())

    # Restart from beginning + LED flash (using the sequence that worked for you)
    inst.write("OUTP:SYNC OFF")
    inst.write("FUNC USER")
    inst.write("OUTP OFF")
    inst.write("OUTP ON")
    time.sleep(0.05)
    inst.write("OUTP:SYNC ON")
    time.sleep(0.2)
    inst.write("OUTP:SYNC OFF")
    print("Output ON + Sync LED flashed. Trial running.")
    print("Final error:", inst.query("SYST:ERR?").strip())
    inst.close()

if __name__ == "__main__":
    main()