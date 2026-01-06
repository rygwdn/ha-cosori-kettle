# Cosori Kettle Python Library

A standalone Python library for controlling Cosori Smart Kettles via Bluetooth Low Energy.

**For library overview and architecture, see [LIBRARY.md](../../../LIBRARY.md) in the repository root.**

## Quick Start

```python
import asyncio
from bleak import BleakScanner
from custom_components.cosori_kettle_ble.cosori_kettle import CosoriKettle

async def main():
    # Find your kettle
    device = await BleakScanner.find_device_by_address("AA:BB:CC:DD:EE:FF")

    # Connect and control
    async with CosoriKettle(device, "AA:BB:CC:DD:EE:FF") as kettle:
        # Boil water
        await kettle.boil()

        # Check status
        print(f"Temperature: {kettle.temperature}°F")
        print(f"Heating: {kettle.is_heating}")
        print(f"On base: {kettle.is_on_base}")

        # Heat to specific temperature
        await kettle.heat_to_temperature(180)

        # Use preset modes
        await kettle.heat_for_green_tea()
        await kettle.heat_for_coffee()

        # Stop heating
        await kettle.stop_heating()

asyncio.run(main())
```

## API Reference

### CosoriKettle

High-level async controller for the kettle.

**Methods:**
- `async connect()` - Connect to the kettle
- `async disconnect()` - Disconnect from the kettle
- `async update_status()` - Request status update
- `async boil(hold_time_seconds=0)` - Boil water to 212°F
- `async heat_to_temperature(temp_f, hold_time_seconds=0)` - Heat to custom temperature
- `async heat_for_green_tea(hold_time_seconds=0)` - Heat to 180°F
- `async heat_for_oolong_tea(hold_time_seconds=0)` - Heat to 195°F
- `async heat_for_coffee(hold_time_seconds=0)` - Heat to 205°F
- `async stop_heating()` - Stop current heating operation
- `async set_my_temp(temp_f)` - Set custom temperature preference
- `async set_baby_formula_mode(enabled)` - Enable/disable baby formula mode

**Properties:**
- `is_connected: bool` - Connection status
- `status: ExtendedStatus | None` - Current kettle status
- `temperature: int | None` - Current temperature in °F
- `is_heating: bool` - Whether kettle is currently heating
- `is_on_base: bool` - Whether kettle is on charging base
- `setpoint: int | None` - Target temperature in °F

### ExtendedStatus

Status information from the kettle.

**Fields:**
- `temp: int` - Current temperature (°F)
- `setpoint: int` - Target temperature (°F)
- `stage: int` - Heating stage (0=idle, 1=heating)
- `mode: int` - Operating mode
- `my_temp: int` - Custom temperature setting
- `on_base: bool` - Whether on charging base
- `remaining_hold_time: int` - Seconds remaining in keep-warm
- `baby_formula_enabled: bool` - Baby formula mode status
- `valid: bool` - Whether status is valid

## Installation

This library is embedded within the Home Assistant component.

### In This Repository

```python
from custom_components.cosori_kettle_ble.cosori_kettle import CosoriKettle
```

### Standalone Usage

1. Copy the `custom_components/cosori_kettle_ble/cosori_kettle/` directory to your project
2. Install dependencies: `pip install bleak>=0.21.0`
3. Import using the path where you placed it

## Protocol Details

All temperatures are in Fahrenheit. The library automatically detects protocol version (V0/V1) from firmware version and handles all BLE communication details.

See [PROTOCOL.md](../../../PROTOCOL.md) for complete protocol documentation.

## Examples

Interactive examples in repository root `examples/`:

```bash
# Interactive control
python examples/interactive.py [MAC_ADDRESS]

# Simple boil example
python examples/simple.py
```

## Testing

```bash
# Run library tests (from repository root)
uv run --extra test pytest tests/library/ -v
```

## License

MIT License - see LICENSE file for details
