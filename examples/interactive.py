#!/usr/bin/env python3
"""Interactive example for controlling Cosori Kettle.

This script demonstrates how to use the cosori-kettle library to
connect to and control a Cosori Smart Kettle.
"""
import asyncio
import logging
import sys

from bleak import BleakScanner

from custom_components.cosori_kettle_ble.cosori_kettle import CosoriKettle, ExtendedStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def on_status_update(status: ExtendedStatus):
    """Callback for status updates."""
    print(f"\n📊 Status Update:")
    print(f"  Temperature: {status.temp}°F (target: {status.setpoint}°F)")
    print(f"  Heating: {'Yes' if status.stage > 0 else 'No'}")
    print(f"  On Base: {'Yes' if status.on_base else 'No'}")
    print(f"  My Temp: {status.my_temp}°F")
    if status.remaining_hold_time > 0:
        print(f"  Hold Time Remaining: {status.remaining_hold_time}s")


async def scan_for_kettles():
    """Scan for Cosori Kettles."""
    print("🔍 Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=5.0)

    kettles = []
    for device in devices:
        # Cosori kettles typically have "Cosori" in the name
        if device.name and "cosori" in device.name.lower():
            kettles.append(device)
            print(f"  Found: {device.name} ({device.address})")

    if not kettles:
        print("  No Cosori kettles found. Please ensure:")
        print("  - Kettle is powered on")
        print("  - Kettle is on the base")
        print("  - Bluetooth is enabled")

    return kettles


async def interactive_mode(kettle: CosoriKettle):
    """Interactive control mode."""
    print("\n🎮 Interactive Mode")
    print("Commands:")
    print("  1 - Boil water (212°F)")
    print("  2 - Green tea (180°F)")
    print("  3 - Oolong tea (195°F)")
    print("  4 - Coffee (205°F)")
    print("  5 - Custom temperature")
    print("  s - Get status")
    print("  x - Stop heating")
    print("  q - Quit")

    while True:
        command = input("\n> ").strip().lower()

        try:
            if command == "1":
                print("🔥 Boiling water...")
                await kettle.boil()
            elif command == "2":
                print("🍵 Heating for green tea...")
                await kettle.heat_for_green_tea()
            elif command == "3":
                print("🍵 Heating for oolong tea...")
                await kettle.heat_for_oolong_tea()
            elif command == "4":
                print("☕ Heating for coffee...")
                await kettle.heat_for_coffee()
            elif command == "5":
                temp = input("Enter temperature (104-212°F): ")
                temp_f = int(temp)
                if 104 <= temp_f <= 212:
                    print(f"🌡️  Heating to {temp_f}°F...")
                    await kettle.heat_to_temperature(temp_f)
                else:
                    print("❌ Temperature must be between 104-212°F")
            elif command == "s":
                print("📊 Requesting status...")
                await kettle.update_status()
                await asyncio.sleep(0.5)
                if kettle.status:
                    on_status_update(kettle.status)
            elif command == "x":
                print("⏹️  Stopping heating...")
                await kettle.stop_heating()
            elif command == "q":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Unknown command")

        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Main function."""
    print("🫖 Cosori Kettle Interactive Control\n")

    # Check for command line argument (MAC address)
    if len(sys.argv) > 1:
        mac_address = sys.argv[1]
        print(f"🔗 Connecting to {mac_address}...")
        device = await BleakScanner.find_device_by_address(mac_address, timeout=5.0)
        if not device:
            print(f"❌ Device {mac_address} not found")
            return
    else:
        # Scan for kettles
        kettles = await scan_for_kettles()
        if not kettles:
            return

        # Use first kettle found
        device = kettles[0]
        mac_address = device.address
        print(f"\n🔗 Connecting to {device.name} ({mac_address})...")

    # Connect and control
    try:
        async with CosoriKettle(device, mac_address, status_callback=on_status_update) as kettle:
            print("✅ Connected!")

            # Get initial status
            print("\n📊 Getting initial status...")
            await kettle.update_status()
            await asyncio.sleep(1.0)

            # Enter interactive mode
            await interactive_mode(kettle)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
