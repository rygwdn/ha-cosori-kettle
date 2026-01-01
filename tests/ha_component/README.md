# Home Assistant Component Tests

These tests validate the Python protocol implementation in the Cosori Kettle BLE Home Assistant custom component, ensuring parity with the C++ implementation used in the ESPHome component.

## Running Tests

```bash
# Run Python protocol tests
make test-pytest

# Run C++ protocol tests
make test-cpp

# Run all tests (C++ + Python)
make test-all
# or simply
make test
```

## Test Coverage

### Protocol Tests (`test_protocol.py`)

Ported from `tests/test_cpp.cpp`, these tests verify:

- **Envelope Building**: Packet framing with magic bytes, sequence numbers, checksums
- **Envelope Parsing**: Frame extraction, validation, multi-frame handling
- **Protocol Building**: Command payload generation (status requests, set temp, set mode, stop, etc.)
- **Protocol Parsing**: Status packet parsing (compact and extended)
- **Round-trip**: Build → envelope → parse verification
- **Real Packets**: Validation against actual device packet captures

All tests ensure the Python implementation behaves identically to the C++ version.

## Requirements

- pytest >= 8.0.0
- pytest-asyncio >= 0.23.0

These are automatically installed when running `make test-pytest`.
