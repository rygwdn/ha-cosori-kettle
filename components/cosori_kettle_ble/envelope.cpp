#include "envelope.h"

namespace esphome {
namespace cosori_kettle_ble {

// Protocol constants are now defined in envelope.h

uint8_t Envelope::calculate_checksum(uint8_t frame_type, uint8_t seq, uint16_t payload_len) {
  return (FRAME_MAGIC + frame_type + seq + (payload_len & 0xFF) + ((payload_len >> 8) & 0xFF)) & 0xFF;
}

}  // namespace cosori_kettle_ble
}  // namespace esphome
