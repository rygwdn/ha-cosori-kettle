# Cosori Kettle Python Library

A standalone Python library for controlling Cosori Smart Kettles via Bluetooth Low Energy.

## Features

- Full BLE protocol implementation for Cosori kettles
- Async/await support using `bleak`
- High-level API for common operations
- Low-level protocol access for advanced use
- Type hints and dataclasses for better IDE support
- Independent of Home Assistant

## Installation

```bash
pip install cosori-kettle
```

Or install from source:

```bash
cd cosori_kettle
pip install .
```

## Quick Start

```python
import asyncio
from bleak import BleakScanner
from cosori_kettle import CosoriKettle

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

## Advanced Usage

### Status Monitoring

```python
from cosori_kettle import CosoriKettle

def on_status_update(status):
    print(f"Temp: {status.temp}°F, Heating: {status.stage > 0}")

async with CosoriKettle(device, mac, status_callback=on_status_update) as kettle:
    # Status updates will call the callback
    await kettle.update_status()
```

### Low-Level Protocol Access

```python
from cosori_kettle import CosoriKettleBLEClient
from cosori_kettle.protocol import (
    build_status_request_frame,
    parse_extended_status,
    PROTOCOL_VERSION_V1
)

client = CosoriKettleBLEClient(device)
await client.connect()

# Send custom frame
frame = build_status_request_frame(PROTOCOL_VERSION_V1, seq=0)
await client.send_frame(frame)

await client.disconnect()
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

## Protocol Details

All temperatures are in Fahrenheit. The library handles:
- BLE packet framing and checksums
- Request/response flow with ACK handling
- Status parsing from compact and extended formats
- On-base detection
- Hold/keep-warm timer management

See [PROTOCOL.md](../PROTOCOL.md) for complete protocol documentation.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run example
python examples/interactive.py
```

## License

MIT License - see LICENSE file for details
