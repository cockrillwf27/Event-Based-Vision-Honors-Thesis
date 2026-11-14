#!/usr/bin/env python3
"""Restart the 33220A arb and flash the Sync LED once at the start."""
import pyvisa
import time

RESOURCE = "USB0::0x0957::0x0407::MY43005577::0::INSTR"
FLASH_MS = 400          # make the flash a little longer

def main():
    rm = pyvisa.ResourceManager()
    inst = rm.open_resource(RESOURCE)
    inst.timeout = 5000

    # Ensure Sync is off, then restart the arb cleanly
    inst.write("OUTP:SYNC OFF")
    inst.write("FUNC USER")
    inst.write("OUTP OFF")
    inst.write("OUTP ON")
    time.sleep(0.05)

    # Flash the LED
    inst.write("OUTP:SYNC ON")
    time.sleep(FLASH_MS / 1000)
    inst.write("OUTP:SYNC OFF")

    inst.close()
    print(f"Arb restarted. Sync flashed for {FLASH_MS} ms.")

if __name__ == "__main__":
    main()