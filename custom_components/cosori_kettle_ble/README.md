# Cosori Kettle BLE - Home Assistant Integration

Home Assistant custom component for controlling Cosori smart kettles via Bluetooth Low Energy (BLE).

## Features

- **Climate Entity**: Main kettle control with preset modes (Boil, Green Tea, Oolong, Coffee)
- **Temperature Control**: Set custom target temperatures (104-212°F)
- **Sensors**:
  - Current temperature
  - Target temperature
  - My Temp setting
  - Operating mode
  - Remaining hold time
- **Binary Sensors**:
  - On base detection
  - Heating status
- **Switches**:
  - Baby formula mode

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Install "Cosori Kettle BLE" from HACS
3. Restart Home Assistant
4. Go to Settings > Devices & Services > Add Integration
5. Search for "Cosori Kettle BLE" and add your kettle

### Manual Installation

1. Copy the `custom_components/cosori_kettle_ble` directory to your Home Assistant `custom_components` folder
2. Restart Home Assistant
3. Go to Settings > Devices & Services > Add Integration
4. Search for "Cosori Kettle BLE" and add your kettle

## Configuration

The integration supports automatic discovery via Bluetooth. Your kettle must be:
- Powered on
- Within Bluetooth range of your Home Assistant server
- Previously paired with the Cosori app (to obtain the device ID)

### Device ID

The device ID is the MAC address of your kettle, which also serves as the 16-byte registration key (converted from hex). You can find it using:

```bash
./scan.py
```

Or check your Cosori mobile app settings.

## Usage

### Climate Entity

The climate entity provides full kettle control:

- **HVAC Mode**: Off / Heat
- **Preset Modes**:
  - Boil (212°F)
  - Green Tea (180°F)
  - Oolong (195°F)
  - Coffee (205°F)
- **Target Temperature**: Set custom temperature (104-212°F)

### Services

All standard climate services are supported:

- `climate.turn_on`: Start heating
- `climate.turn_off`: Stop heating
- `climate.set_temperature`: Set target temperature
- `climate.set_preset_mode`: Select preset mode

### Automation Example

```yaml
automation:
  - alias: "Morning Coffee"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.cosori_kettle
        data:
          preset_mode: coffee
```

## Protocol Details

This integration implements the Cosori kettle BLE protocol:

- **Service UUID**: 0000fff0-0000-1000-8000-00805f9b34fb
- **RX Characteristic**: 0000fff1-0000-1000-8000-00805f9b34fb (notifications)
- **TX Characteristic**: 0000fff2-0000-1000-8000-00805f9b34fb (write)
- **Protocol Version**: V1 (with V0 fallback)
- **Temperature Unit**: Fahrenheit (no conversion)

See `PROTOCOL.md` in the repository root for detailed protocol documentation.

## Troubleshooting

### Device Not Found

- Ensure the kettle is powered on and on its base
- Check that Bluetooth is enabled on your Home Assistant server
- Verify the kettle is within Bluetooth range
- Try power cycling the kettle

### Connection Issues

- The integration polls the kettle every 2 seconds
- Connection is automatically re-established if lost
- Check Home Assistant logs for detailed error messages

### Temperature Reading Issues

- Kettle must be on the base for accurate readings
- Wait a few seconds after placing on base for connection
- Off-base detection may show stale temperature data

## Development

This component is based on the ESPHome `cosori_kettle_ble` component, ported to use Home Assistant's native BLE integration.

Repository: https://github.com/rygwdn/CosoriKettleBLE

## License

See repository LICENSE file.
