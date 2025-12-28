#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "bleak",
# ]
# ///

import asyncio
from bleak import BleakScanner, BleakClient
import logging

logger = logging.getLogger(__name__)

async def main():
    # devices = await BleakScanner.discover(cb=CBScannerArgs(use_bdaddr=True))
    # for d in devices:
    #     if d.name and ("cosori" in d.name.lower() or "kettle" in d.name.lower()):
    #         print(f"Found: {d.name} - {d.address}")
    logging.basicConfig(
        level=logging.INFO,
        #format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
        format="%(message)s",
    )

    device = await BleakScanner.find_device_by_name(
        "Cosori Gooseneck Kettle", cb={"use_bdaddr": True}
    )
    if device is None:
        logger.error("could not find device")
        return

    print(f"Found: {device.name} - {device.address}")

    async with BleakClient(
        device,
        pair=False,
        # Give the user plenty of time to enter a PIN code if paring is required.
        #timeout=10,
    ) as client:
        logger.info("connected to %s (%s)", client.name, client.address)

        for service in client.services:
            logger.info("[Service] %s (Handle: 0x%04x): %s", service.uuid, service.handle + 1, service.description)

            for char in service.characteristics:
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char)
                        extra = f", Value: {value}"
                    except Exception as e:
                        extra = f", Error: {e}"
                else:
                    extra = ""

                if "write-without-response" in char.properties:
                    extra += f", Max write w/o rsp size: {char.max_write_without_response_size}"

                # import pprint; pprint.pprint({
                #     "desc": char.description,
                #     "a": char.handle,
                #     "b": char.properties,
                #     "c": char.uuid,
                # })
                logger.info(
                    "  [Characteristic] %s (Handle: 0x%04x): %s (%s)%s",
                    char.uuid,
                    char.handle + 1,
                    char.description,
                    ",".join(char.properties),
                    extra,
                )

                for descriptor in char.descriptors:
                    try:
                        value = await client.read_gatt_descriptor(descriptor)
                        logger.info("    [Descriptor] %s (Handle: 0x%04x): %s, Value: %r", descriptor.uuid, descriptor.handle + 1, descriptor.description, value)
                    except Exception as e:
                        logger.error("    [Descriptor] %s (Handle: 0x%04x): %s, Error: %s", descriptor.uuid, descriptor.handle + 1, descriptor.description, e)

        logger.info("disconnecting...")

    logger.info("disconnected")

asyncio.run(main())



"""
connected to Cosori Gooseneck Kettle (04:57:91:74:3B:F4)
[Service] 0000180a-0000-1000-8000-00805f9b34fb (Handle: 7): Device Information
  [Characteristic] 00002a27-0000-1000-8000-00805f9b34fb (Handle: 8): Hardware Revision String (read), Value: bytearray(b'1.0.00')
  [Characteristic] 00002a28-0000-1000-8000-00805f9b34fb (Handle: 10): Software Revision String (read), Value: bytearray(b'R0007V0012')

# Comm
[Service] 0000fff0-0000-1000-8000-00805f9b34fb (Handle: 12): Vendor specific
  [Characteristic] 0000fff2-0000-1000-8000-00805f9b34fb (Handle: 13): Vendor specific (write,write-without-response), Max write w/o rsp size: 128
  [Characteristic] 0000fff1-0000-1000-8000-00805f9b34fb (Handle: 15): Vendor specific (notify)
    [Descriptor] 00002902-0000-1000-8000-00805f9b34fb (Handle: 17): Client Characteristic Configuration, Value: bytearray(b'')

# Firmware OTA
[Service] f000ffc0-0451-4000-b000-000000000000 (Handle: 18): Unknown
  [Characteristic] f000ffc1-0451-4000-b000-000000000000 (Handle: 19): Unknown (notify,write,write-without-response), Max write w/o rsp size: 128
    [Descriptor] 00002902-0000-1000-8000-00805f9b34fb (Handle: 21): Client Characteristic Configuration, Value: bytearray(b'')
    [Descriptor] 00002901-0000-1000-8000-00805f9b34fb (Handle: 22): Characteristic User Description, Value: bytearray(b'Img Identify')
  [Characteristic] f000ffc2-0451-4000-b000-000000000000 (Handle: 23): Unknown (notify,write,write-without-response), Max write w/o rsp size: 128
    [Descriptor] 00002902-0000-1000-8000-00805f9b34fb (Handle: 25): Client Characteristic Configuration, Value: bytearray(b'')
    [Descriptor] 00002901-0000-1000-8000-00805f9b34fb (Handle: 26): Characteristic User Description, Value: bytearray(b'Img Block')

# Data Example

bytes.fromhex('a5220024000181d1003939303365303161336333626161386636633731636262353136376537643566')

a522 00 2400 a4 0181d10039393033653031613363
a522 01 2400 ec 0181d10039393033653031613363 (chunk 1 of 2)

3362616138663663373163626235313637653764
3362616138663663373163626235313637653764 (chunk 2 of 2)

3566
3566 (chunk 3 of 2)


Info                                                            Value
Sent Read By Type Request, Characteristic, Handles: 0x0006..0x0006 
Rcvd Error Response - Attribute Not Found, Handle: 0x0006 (Unknown) 
Sent Read Request, Handle: 0x0009 (Unknown)                     
Rcvd Read Response, Handle: 0x0009 (Unknown)                    312e302e3030 # Hardware revision
Sent Read Request, Handle: 0x000b (Unknown)                     
Rcvd Read Response, Handle: 0x000b (Unknown)                    52303030375630303132 # Softwqre revision
Sent Write Request, Handle: 0x0011 (Unknown)                    0100
Rcvd Write Response, Handle: 0x0011 (Unknown)                   
Sent Write Request, Handle: 0x0019 (Unknown)                    0100
Rcvd Write Response, Handle: 0x0019 (Unknown)                   
Sent Write Request, Handle: 0x000e (Unknown)                    a522002400a40181d10039393033653031613363
Rcvd Write Response, Handle: 0x000e (Unknown)                   
Sent Write Request, Handle: 0x000e (Unknown)                    3362616138663663373163626235313637653764
Rcvd Write Response, Handle: 0x000e (Unknown)                   
Sent Write Request, Handle: 0x000e (Unknown)                    3566
Rcvd Write Response, Handle: 0x000e (Unknown)                   
Rcvd Handle Value Notification, Handle: 0x0010 (Unknown)        a512000500f00181d10000
Sent Write Request, Handle: 0x000e (Unknown)                    a522022400a20181d10039393033653031613363
Rcvd Write Response, Handle: 0x000e (Unknown)                   
Sent Write Request, Handle: 0x000e (Unknown)                    3362616138663663373163626235313637653764
Rcvd Write Response, Handle: 0x000e (Unknown)                   
Sent Write Request, Handle: 0x000e (Unknown)                    3566
Rcvd Write Response, Handle: 0x000e (Unknown)                   
Rcvd Handle Value Notification, Handle: 0x0010 (Unknown)        a512020500ee0181d10000
Sent Write Request, Handle: 0x000e (Unknown)                    a522010400b201404000
Rcvd Write Response, Handle: 0x000e (Unknown)                   
Rcvd Handle Value Notification, Handle: 0x0010 (Unknown)        a512011d00de014040000000d45b8c0000000000000000000000000000000807000001
Sent Read By Type Request, Device Name, Handles: 0x0001..0x0005 
Rcvd Read By Type Response, Attribute List Length: 1            
Sent Write Request, Handle: 0x000e (Unknown)                    a5220309009501f0a3000300000000
Rcvd Write Response, Handle: 0x000e (Unknown)                   
Rcvd Handle Value Notification, Handle: 0x0010 (Unknown)        a512030400ad01f0a300
Rcvd Handle Value Notification, Handle: 0x0010 (Unknown)        a5229d0c00e1014140000103cd5b00000000
Sent Write Request, Handle: 0x000e (Unknown)                    a5220404009801f4a300
Rcvd Write Response, Handle: 0x000e (Unknown)                   
Rcvd Handle Value Notification, Handle: 0x0010 (Unknown)        a512040400a801f4a300
Rcvd Handle Value Notification, Handle: 0x0010 (Unknown)        a5229e0c00e4014140000000cd5b00000000
"""
