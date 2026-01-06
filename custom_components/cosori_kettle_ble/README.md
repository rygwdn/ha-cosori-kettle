# Cosori Kettle BLE - Home Assistant Integration

Home Assistant custom component for controlling Cosori smart kettles via Bluetooth Low Energy (BLE).

**For complete documentation, installation instructions, and usage examples, see the [main README](../../README.md).**

## Quick Links

- **Installation**: See [Option 2: Home Assistant Integration](../../README.md#option-2-home-assistant-integration) in main README
- **Usage Examples**: See [Usage Examples](../../README.md#usage-examples) in main README
- **Troubleshooting**: See [Troubleshooting](../../README.md#troubleshooting) in main README
- **Protocol Details**: See [PROTOCOL.md](../../PROTOCOL.md)

## Features

- Climate entity with preset modes (Boil, Green Tea, Oolong, Coffee)
- Temperature sensors and control
- On-base detection
- Heating status
- Baby formula mode switch
- Automatic protocol version detection (V0/V1)

## Important Notes

- **The kettle only supports ONE BLE connection at a time.** Disconnect from the official app before using this integration.
- Automatic Bluetooth discovery is supported
- All temperatures are in Fahrenheit (converted automatically by Home Assistant)
