# Cosori Kettle Python Library

A standalone Python library for controlling Cosori Smart Kettles via Bluetooth Low Energy, embedded within the Home Assistant component.

## Structure

```
custom_components/cosori_kettle_ble/cosori_kettle/
├── __init__.py          # Public API exports
├── protocol.py          # Low-level BLE protocol (frames, parsing, checksums)
├── client.py            # BLE communication layer (using bleak)
├── kettle.py            # High-level kettle controller API
└── README.md            # Library documentation
```

## Key Components

### 1. Protocol Layer (`protocol.py`)

Pure Python implementation of the Cosori kettle BLE protocol:

- **Frame Building**: Construct BLE packets with proper headers and checksums
- **Frame Parsing**: Parse incoming BLE notifications
- **Status Decoding**: Extract kettle state from status packets
- **No Dependencies**: Only uses Python standard library

Key functions:
- `build_hello_frame()` - Authentication
- `build_status_request_frame()` - Poll for status
- `build_set_mode_frame()` - Start heating
- `build_stop_frame()` - Stop heating
- `parse_extended_status()` - Decode status packets
- `parse_frames()` - Parse buffered BLE data

### 2. BLE Client Layer (`client.py`)

Handles Bluetooth Low Energy communication using `bleak`:

- **Connection Management**: Connect/disconnect from kettle
- **Notification Handling**: Receive and buffer BLE notifications
- **ACK Management**: Wait for acknowledgments with timeout
- **Frame Send/Receive**: Handle BLE chunking and flow control

Key class:
- `CosoriKettleBLEClient` - Low-level BLE client

### 3. High-Level Controller (`kettle.py`)

User-friendly async API for common operations:

- **Connection**: Async context manager support
- **Heating Control**: Boil, heat to temperature, preset modes
- **Status Monitoring**: Real-time status updates
- **Callbacks**: Optional status change notifications

Key class:
- `CosoriKettle` - Main controller class

Methods:
- `async boil()` - Boil water to 212°F
- `async heat_to_temperature(temp_f)` - Heat to custom temperature
- `async heat_for_green_tea()` - 180°F
- `async heat_for_coffee()` - 205°F
- `async stop_heating()` - Stop current operation
- `async update_status()` - Poll for status
- Properties: `temperature`, `is_heating`, `is_on_base`, etc.

## Usage Examples

### Simple Usage

```python
from bleak import BleakScanner
from custom_components.cosori_kettle_ble.cosori_kettle import CosoriKettle

# Find and connect
device = await BleakScanner.find_device_by_address("AA:BB:CC:DD:EE:FF")

async with CosoriKettle(device, "AA:BB:CC:DD:EE:FF") as kettle:
    await kettle.boil()
    print(f"Temperature: {kettle.temperature}°F")
```

### Status Monitoring

```python
def on_status(status):
    print(f"Temp: {status.temp}°F, Heating: {status.stage > 0}")

async with CosoriKettle(device, mac, status_callback=on_status) as kettle:
    while True:
        await kettle.update_status()
        await asyncio.sleep(2)
```

### Low-Level Protocol Access

```python
from custom_components.cosori_kettle_ble.cosori_kettle import CosoriKettleBLEClient
from custom_components.cosori_kettle_ble.cosori_kettle.protocol import (
    build_status_request_frame,
    PROTOCOL_VERSION_V1
)

client = CosoriKettleBLEClient(device)
await client.connect()

frame = build_status_request_frame(PROTOCOL_VERSION_V1, seq=0)
await client.send_frame(frame)

await client.disconnect()
```

## Integration

The library is embedded within the Home Assistant component at `custom_components/cosori_kettle_ble/cosori_kettle/`, providing a single source of truth for protocol logic that can be tested independently.

## Testing

The library has its own test suite:

```bash
# Run library tests
uv run --extra test pytest tests/library/ -v

# Run HA component tests
uv run --extra test pytest tests/ha_component/ -v

# Run all tests
uv run --extra test pytest -v
```

Tests cover:
- Frame building and parsing
- Checksum validation
- Status parsing (on-base detection, temperatures, etc.)
- Protocol version detection

## Examples

Interactive examples are provided in `examples/`:

```bash
# Interactive control
python examples/interactive.py [MAC_ADDRESS]

# Simple boil example
python examples/simple.py
```

The interactive example provides a command-line interface for:
- Boiling water
- Preset tea/coffee temperatures
- Custom temperatures
- Real-time status monitoring
- Stop heating

## Dependencies

Library dependencies (minimal):
- `bleak>=0.21.0` - Bluetooth Low Energy communication

Development dependencies:
- `pytest>=8.0.0`
- `pytest-asyncio>=0.23.0`

## Installation

### In This Project

The library is embedded within the Home Assistant component. When working in this repository, you can import it directly:

```python
from custom_components.cosori_kettle_ble.cosori_kettle import CosoriKettle
```

### Standalone Usage

To use the library in another project, you can:

1. Copy the `custom_components/cosori_kettle_ble/cosori_kettle/` directory to your project
2. Install dependencies: `pip install bleak>=0.21.0`
3. Import using the path where you placed it

## Protocol Details

All temperatures are in Fahrenheit. The library automatically detects protocol version (V0/V1) from firmware version and handles all BLE communication details.

See [PROTOCOL.md](PROTOCOL.md) for complete protocol documentation.


## License

MIT License - see LICENSE file for details
