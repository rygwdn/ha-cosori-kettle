#!/usr/bin/env python3
"""Simple example showing basic kettle control."""
import asyncio
import sys

from bleak import BleakScanner

from custom_components.cosori_kettle_ble.cosori_kettle import CosoriKettle


async def main():
    # Replace with your kettle's MAC address
    MAC_ADDRESS = "AA:BB:CC:DD:EE:FF"

    # Find device
    print(f"Connecting to {MAC_ADDRESS}...")
    device = await BleakScanner.find_device_by_address(MAC_ADDRESS)

    if not device:
        print("Device not found")
        return

    # Connect and control
    async with CosoriKettle(device, MAC_ADDRESS) as kettle:
        print("Connected!")

        # Get status
        await kettle.update_status()
        print(f"Temperature: {kettle.temperature}°F")
        print(f"Heating: {kettle.is_heating}")
        print(f"On base: {kettle.is_on_base}")

        # Boil water
        print("\nBoiling water...")
        await kettle.boil()

        # Wait for heating to start
        await asyncio.sleep(2)
        await kettle.update_status()
        print(f"Heating: {kettle.is_heating}")

        # Stop after 5 seconds
        await asyncio.sleep(5)
        print("Stopping...")
        await kettle.stop_heating()


if __name__ == "__main__":
    asyncio.run(main())
