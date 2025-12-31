#include "cosori_kettle_state.h"
#include "protocol.h"
#include <cmath>
#include <cstring>
#include <cstdarg>
#include <cstdio>

namespace esphome {
namespace cosori_kettle_ble {

// Buffer size limits
static constexpr size_t MAX_FRAME_BUFFER_SIZE = 512;
static constexpr size_t MAX_PAYLOAD_SIZE = 256;

// Timing constants (milliseconds)
static constexpr uint32_t HANDSHAKE_TIMEOUT_MS = 5000;
static constexpr uint32_t PRE_SETPOINT_DELAY_MS = 60;
static constexpr uint32_t POST_SETPOINT_DELAY_MS = 100;
static constexpr uint32_t CONTROL_DELAY_MS = 50;
static constexpr uint32_t STATUS_TIMEOUT_MS = 2000;
static constexpr uint32_t IDLE_TIMEOUT_MS = 30000;

// Online/offline tracking
static constexpr uint8_t NO_RESPONSE_THRESHOLD = 10;

// ============================================================================
// Constructor and Configuration
// ============================================================================

CosoriKettleState::CosoriKettleState(const Config& config)
  : config_(config),
    state_(),
    send_data_callback_(nullptr),
    log_callback_(nullptr),
    last_rx_seq_(0),
    tx_seq_(0),
    last_ack_error_code_(0),
    waiting_for_ack_complete_(false),
    waiting_for_ack_seq_(0),
    last_status_seq_(0),
    send_buffer_(),
    recv_buffer_(),
    send_chunk_index_(0),
    send_total_chunks_(0),
    waiting_for_write_ack_(false),
    pending_hold_time_(false),
    pending_my_temp_(false),
    pending_baby_formula_(false),
    command_state_(CommandState::IDLE),
    command_state_time_(0),
    pending_mode_(0),
    pending_temp_f_(0),
    use_register_command_(false) {
}

void CosoriKettleState::set_registration_key(const std::array<uint8_t, 16>& key) {
  config_.registration_key = key;
  config_.registration_key_set = true;
}

void CosoriKettleState::reset() {
  recv_buffer_.clear();
  state_.status_received = false;
  state_.no_response_count = 0;
  send_chunk_index_ = 0;
  send_total_chunks_ = 0;
  waiting_for_write_ack_ = false;
}

// ============================================================================
// Logging
// ============================================================================

void CosoriKettleState::log(int level, const char* format, ...) {
  if (!log_callback_) {
    return;
  }

  char buffer[256];
  va_list args;
  va_start(args, format);
  vsnprintf(buffer, sizeof(buffer), format, args);
  va_end(args);

  log_callback_(level, buffer);
}

// ============================================================================
// Data Processing
// ============================================================================

void CosoriKettleState::process_rx_data(const uint8_t* data, size_t len) {
  // Check buffer size limit before appending
  if (recv_buffer_.size() + len > MAX_FRAME_BUFFER_SIZE) {
    log(1, "Frame buffer overflow, clearing buffer");
    recv_buffer_.clear();
  }

  // Append to receive buffer
  if (!recv_buffer_.append(data, len)) {
    log(1, "Failed to append to receive buffer, clearing");
    recv_buffer_.clear();
  }

  // Process complete frames
  process_frame_buffer();
}

void CosoriKettleState::on_write_ack(bool success) {
  if (!waiting_for_write_ack_) {
    return;
  }

  if (success) {
    // Move to next chunk
    send_chunk_index_++;
    waiting_for_write_ack_ = false;
    // Send next chunk if available
    send_next_chunk();
  } else {
    log(1, "Write failed");
    send_chunk_index_ = 0;
    send_total_chunks_ = 0;
    waiting_for_write_ack_ = false;
  }
}

// ============================================================================
// Update Loop
// ============================================================================

void CosoriKettleState::update(uint32_t now_ms, bool connected, bool registration_sent) {
  track_online_status();

  if (!connected) {
    return;
  }

  if (!registration_sent) {
    return;
  }

  // Process command state machine
  process_command_state_machine(now_ms);

  if (command_state_ != CommandState::IDLE) {
    return;
  }

  if (waiting_for_write_ack_) {
    return;
  }

  if (send_chunk_index_ < send_total_chunks_) {
    return;
  }

  send_status_request();
}

// ============================================================================
// Command Methods
// ============================================================================

void CosoriKettleState::set_target_setpoint(float temp_f) {
  // Clamp to valid range
  if (temp_f < MIN_TEMP_F)
    temp_f = MIN_TEMP_F;
  if (temp_f > MAX_TEMP_F)
    temp_f = MAX_TEMP_F;

  state_.target_setpoint_f = temp_f;
  log(2, "Target setpoint changed to %.0f°F", temp_f);
}

void CosoriKettleState::set_hold_time(uint16_t seconds) {
  state_.hold_time_seconds = seconds;
  pending_hold_time_ = true;
  log(2, "Hold time changed to %u seconds", seconds);

  // Send command to device
  send_set_hold_time(seconds);
}

void CosoriKettleState::set_my_temp(uint8_t temp_f) {
  // Clamp to valid range
  if (temp_f < MIN_TEMP_F)
    temp_f = MIN_TEMP_F;
  if (temp_f > MAX_TEMP_F)
    temp_f = MAX_TEMP_F;

  state_.my_temp_f = temp_f;
  pending_my_temp_ = true;
  log(2, "My temp changed to %d°F", temp_f);

  // Send command to device
  send_set_my_temp(temp_f);
}

void CosoriKettleState::set_baby_formula_enabled(bool enabled) {
  state_.baby_formula_enabled = enabled;
  pending_baby_formula_ = true;
  log(2, "Baby formula mode changed to %s", enabled ? "enabled" : "disabled");

  // Send command to device
  send_set_baby_formula(enabled);
}

void CosoriKettleState::start_heating() {
  uint8_t temp_f = static_cast<uint8_t>(std::round(state_.target_setpoint_f));
  uint8_t mode = (temp_f == MAX_TEMP_F) ? MODE_BOIL : MODE_HEAT;
  auto new_command_state = CommandState::HEAT_START;

  if (config_.protocol_version == 1 && mode == MODE_HEAT) {
    // V1 doesn't support MODE_HEAT, so we need to use mytemp or set mode first
    if (temp_f < MODE_GREEN_TEA_F + 2 && temp_f > MODE_GREEN_TEA_F - 2) {
      mode = MODE_GREEN_TEA;
    } else if (temp_f < MODE_OOLONG_F + 2 && temp_f > MODE_OOLONG_F - 2) {
      mode = MODE_OOLONG;
    } else if (temp_f < MODE_COFFEE_F + 2 && temp_f > MODE_COFFEE_F - 2) {
      mode = MODE_COFFEE;
    } else {
      mode = MODE_MY_TEMP;
      new_command_state = CommandState::HEAT_SET_TEMP;
    }
  }

  log(2, "Starting kettle at %.0f°F using mode %d", state_.target_setpoint_f, mode);

  // Store parameters and start state machine
  pending_temp_f_ = temp_f;
  pending_mode_ = mode;
  command_state_ = new_command_state;
  command_state_time_ = 0;  // Will be set by caller
}

void CosoriKettleState::stop_heating() {
  log(2, "Stopping kettle");

  // Start stop sequence state machine
  command_state_ = CommandState::STOP;
  command_state_time_ = 0;  // Will be set by caller
}

void CosoriKettleState::send_hello(bool use_register_command) {
  // Verify registration key is set
  if (!config_.registration_key_set) {
    log(0, "Registration key not set - cannot send hello/register command");
    return;
  }

  // Start handshake state machine
  use_register_command_ = use_register_command;
  log(2, "Starting handshake (%s)", use_register_command ? "register" : "hello");
  command_state_ = CommandState::HANDSHAKE_START;
  command_state_time_ = 0;  // Will be set by caller
}

void CosoriKettleState::send_status_request() {
  uint8_t seq = next_tx_seq();
  uint8_t payload[4];
  size_t payload_len = build_status_request_payload(config_.protocol_version, payload);
  if (payload_len == 0) {
    log(1, "Failed to build POLL payload");
    return;
  }
  log(2, "Sending POLL (seq=%02x)", seq);
  if (!send_command(seq, payload, payload_len)) {
    log(1, "Failed to send POLL");
  }
}

// ============================================================================
// Internal Methods - Protocol
// ============================================================================

void CosoriKettleState::send_set_my_temp(uint8_t temp_f) {
  uint8_t seq = next_tx_seq();
  uint8_t payload[5];
  size_t payload_len = build_set_my_temp_payload(config_.protocol_version, temp_f, payload);
  if (payload_len == 0) {
    log(1, "Failed to build set my temp payload");
    return;
  }
  log(2, "Sending set my temp %d°F (seq=%02x)", temp_f, seq);
  if (!send_command(seq, payload, payload_len)) {
    log(1, "Failed to send set my temp");
  }
}

void CosoriKettleState::send_set_baby_formula(bool enabled) {
  uint8_t seq = next_tx_seq();
  uint8_t payload[5];
  size_t payload_len = build_set_baby_formula_payload(config_.protocol_version, enabled, payload);
  if (payload_len == 0) {
    log(1, "Failed to build set baby formula payload");
    return;
  }
  log(2, "Sending set baby formula %s (seq=%02x)", enabled ? "enabled" : "disabled", seq);
  if (!send_command(seq, payload, payload_len)) {
    log(1, "Failed to send set baby formula");
  }
}

void CosoriKettleState::send_set_hold_time(uint16_t seconds) {
  uint8_t seq = next_tx_seq();
  uint8_t payload[8];
  size_t payload_len = build_set_hold_time_payload(config_.protocol_version, seconds, payload);
  if (payload_len == 0) {
    log(1, "Failed to build set hold time payload");
    return;
  }
  log(2, "Sending set hold time %u seconds (seq=%02x)", seconds, seq);
  if (!send_command(seq, payload, payload_len)) {
    log(1, "Failed to send set hold time");
  }
}

void CosoriKettleState::send_set_mode(uint8_t mode, uint8_t temp_f) {
  uint8_t seq = next_tx_seq();
  uint8_t payload[9];
  if (config_.protocol_version == 1) {
    if (mode == MODE_HEAT) {
      log(1, "Cannot send set mode: HEAT mode not supported in V1");
      mode = MODE_BOIL;
    }
    if (mode != MODE_MY_TEMP) {
      temp_f = 0;
    }
  }

  size_t payload_len = build_set_mode_payload(config_.protocol_version, mode, temp_f, state_.hold_time_seconds, payload);
  if (payload_len == 0) {
    log(1, "Failed to build set mode payload");
    return;
  }
  log(2, "Sending SETPOINT %d°F (seq=%02x, mode=%02x)", temp_f, seq, mode);
  if (!send_command(seq, payload, payload_len)) {
    log(1, "Failed to send SETPOINT");
  }
}

void CosoriKettleState::send_stop() {
  uint8_t seq = next_tx_seq();
  uint8_t payload[4];
  size_t payload_len = build_stop_payload(config_.protocol_version, payload);
  if (payload_len == 0) {
    log(1, "Failed to build stop payload");
    return;
  }
  log(2, "Sending STOP (seq=%02x)", seq);
  if (!send_command(seq, payload, payload_len)) {
    log(1, "Failed to send STOP");
  }
}

void CosoriKettleState::send_request_compact_status(uint8_t seq_base) {
  uint8_t payload[4];
  size_t payload_len = build_compact_status_request_payload(config_.protocol_version, payload);
  if (payload_len == 0) {
    log(1, "Failed to build compact status request payload");
    return;
  }
  log(2, "Sending request compact status (seq=%02x)", seq_base);
  if (!send_command(seq_base, payload, payload_len, true)) {
    log(1, "Failed to send request compact status");
  }
}

bool CosoriKettleState::send_command(uint8_t seq, const uint8_t* payload, size_t payload_len, bool is_ack) {
  // Check if already sending something or waiting
  if (waiting_for_write_ack_) {
    log(1, "Cannot send command: already waiting for write acknowledgment");
    return false;
  }
  if (send_chunk_index_ < send_total_chunks_) {
    log(1, "Cannot send command: already sending (chunk %zu/%zu)", send_chunk_index_, send_total_chunks_);
    return false;
  }

  // Set payload in send buffer
  bool success;
  if (is_ack) {
    success = send_buffer_.set_ack_payload(seq, payload, payload_len);
  } else {
    success = send_buffer_.set_message_payload(seq, payload, payload_len);
  }

  if (!success) {
    log(1, "Failed to set payload in send buffer");
    return false;
  }

  // Calculate total chunks needed
  send_total_chunks_ = send_buffer_.get_chunk_count();

  if (send_total_chunks_ == 0) {
    log(1, "No chunks to send");
    return false;
  }

  // Reset chunking state
  send_chunk_index_ = 0;
  waiting_for_write_ack_ = false;

  // Send first chunk immediately
  send_next_chunk();
  return true;
}

void CosoriKettleState::send_next_chunk() {
  // Check if we have more chunks to send
  if (send_chunk_index_ >= send_total_chunks_) {
    // All chunks sent
    send_chunk_index_ = 0;
    send_total_chunks_ = 0;
    waiting_for_write_ack_ = false;
    return;
  }

  // Get current chunk data and size
  size_t chunk_size = 0;
  const uint8_t* chunk_data = send_buffer_.get_chunk_data(send_chunk_index_, chunk_size);

  if (chunk_data == nullptr || chunk_size == 0) {
    log(1, "Invalid chunk data at index %zu", send_chunk_index_);
    send_chunk_index_ = 0;
    send_total_chunks_ = 0;
    waiting_for_write_ack_ = false;
    return;
  }

  // Send current chunk via callback
  waiting_for_write_ack_ = true;
  if (send_data_callback_) {
    send_data_callback_(chunk_data, chunk_size);
  } else {
    log(1, "No send data callback set");
    waiting_for_write_ack_ = false;
  }
}

// ============================================================================
// Internal Methods - Frame Processing
// ============================================================================

void CosoriKettleState::process_frame_buffer() {
  while (true) {
    // Process next frame using Envelope's built-in validation and position management
    auto frame = recv_buffer_.process_next_frame(MAX_PAYLOAD_SIZE);

    // If no valid frame found, break (either no more frames or incomplete frame)
    if (!frame.valid) {
      break;
    }

    // Update last RX sequence
    last_rx_seq_ = frame.seq;

    if (frame.frame_type == ACK_HEADER_TYPE) {
      uint8_t ack_status = frame.payload_len > 4 ? static_cast<uint8_t>(frame.payload[4]) : 0;

      if (waiting_for_ack_complete_ && waiting_for_ack_seq_ == frame.seq) {
        waiting_for_ack_complete_ = false;
        last_ack_error_code_ = ack_status;
        log(2, "ACK complete: seq=%02x, error_code=%02x", frame.seq, ack_status);
      }

      if (pending_baby_formula_ && frame.payload[1] == CMD_SET_BABY_FORMULA) {
        pending_baby_formula_ = false;
        log(2, "Baby formula update confirmed: %d", ack_status);
      }

      if (pending_hold_time_ && frame.payload[1] == CMD_SET_HOLD_TIME) {
        pending_hold_time_ = false;
        log(2, "Hold time update confirmed: %d", ack_status);
      }

      if (pending_my_temp_ && frame.payload[1] == CMD_SET_MY_TEMP) {
        pending_my_temp_ = false;
        log(2, "My temp update confirmed: %d", ack_status);
      }
    }

    if (frame.frame_type == MESSAGE_HEADER_TYPE && frame.payload[1] == CMD_CTRL) {
      parse_compact_status(frame.payload, frame.payload_len);
    }

    if (frame.frame_type == ACK_HEADER_TYPE && frame.payload[1] == CMD_POLL) {
      parse_status_ack(frame.payload, frame.payload_len);
    }
  }

  // Compact buffer periodically to free up space at the beginning
  recv_buffer_.compact();
}

void CosoriKettleState::parse_compact_status(const uint8_t* payload, size_t len) {
  CompactStatus status = ::esphome::cosori_kettle_ble::parse_compact_status(payload, len);
  if (!status.valid) {
    return;
  }

  state_.current_temp_f = status.temp;
  state_.kettle_setpoint_f = status.setpoint;
  state_.heating = (status.stage != 0);
  state_.status_received = true;
  last_status_seq_ = last_rx_seq_;

  reset_online_status();
}

void CosoriKettleState::parse_status_ack(const uint8_t* payload, size_t len) {
  ExtendedStatus status = ::esphome::cosori_kettle_ble::parse_extended_status(payload, len);
  if (!status.valid) {
    return;
  }

  state_.current_temp_f = status.temp;
  state_.kettle_setpoint_f = status.setpoint;
  state_.heating = (status.stage != 0);
  state_.status_received = true;
  last_status_seq_ = last_rx_seq_;
  state_.on_base = status.on_base;
  state_.remaining_hold_time_seconds = status.remaining_hold_time;

  if (!pending_my_temp_) {
    state_.my_temp_f = status.my_temp;
  }

  if (!pending_hold_time_) {
    state_.hold_time_seconds = status.configured_hold_time;
  }

  if (!pending_baby_formula_) {
    state_.baby_formula_enabled = status.baby_formula_enabled;
  }

  reset_online_status();
}

// ============================================================================
// Internal Methods - State Machine
// ============================================================================

uint8_t CosoriKettleState::next_tx_seq() {
  if (tx_seq_ == 0 && last_rx_seq_ != 0) {
    tx_seq_ = (last_rx_seq_ + 1) & 0xFF;
  } else {
    tx_seq_ = (tx_seq_ + 1) & 0xFF;
  }
  return tx_seq_;
}

void CosoriKettleState::process_command_state_machine(uint32_t now_ms) {
  // Initialize time on first call
  if (command_state_time_ == 0) {
    command_state_time_ = now_ms;
  }

  uint32_t elapsed = now_ms - command_state_time_;

  const auto initial_state = command_state_;
  if (initial_state != CommandState::IDLE && elapsed) {
    log(2, "Running command state machine in state %d", static_cast<int>(initial_state));
  }

  switch (command_state_) {
    case CommandState::IDLE:
      // Nothing to do
      break;

    case CommandState::HANDSHAKE_START: {
      uint8_t payload[36];
      size_t payload_len;

      // Use register or hello command based on flag
      if (use_register_command_) {
        payload_len = build_register_payload(config_.protocol_version,
                                             config_.registration_key,
                                             payload);
        if (payload_len == 0) {
          log(1, "Failed to build register payload");
          command_state_ = CommandState::IDLE;
          break;
        }
      } else {
        payload_len = build_hello_payload(config_.protocol_version,
                                          config_.registration_key,
                                          payload);
        if (payload_len == 0) {
          log(1, "Failed to build hello payload");
          command_state_ = CommandState::IDLE;
          break;
        }
      }

      // Send command using send_command (seq=0 for handshake)
      const uint8_t sequence_number = 0;
      if (!send_command(sequence_number, payload, payload_len)) {
        log(1, "Failed to send %s command", use_register_command_ ? "register" : "hello");
        command_state_ = CommandState::IDLE;
        break;
      }

      waiting_for_ack_seq_ = sequence_number;
      waiting_for_ack_complete_ = true;

      // Wait for all chunks to be sent before proceeding to poll
      command_state_ = CommandState::HANDSHAKE_WAIT_CHUNKS;
      command_state_time_ = now_ms;
      break;
    }

    case CommandState::HANDSHAKE_WAIT_CHUNKS:
      if (!waiting_for_ack_complete_ && !waiting_for_write_ack_ && send_chunk_index_ >= send_total_chunks_) {
        command_state_ = CommandState::HANDSHAKE_POLL;
        command_state_time_ = now_ms;
      }
      if (elapsed >= HANDSHAKE_TIMEOUT_MS) {
        log(0, "Handshake timeout");
        command_state_ = CommandState::IDLE;
        break;
      }
      break;

    case CommandState::HANDSHAKE_POLL:
      if (!waiting_for_ack_complete_) {
        if (last_ack_error_code_ != 0) {
          log(0, "Error in %s: %d", use_register_command_ ? "registration" : "handshake", last_ack_error_code_);
          command_state_ = CommandState::IDLE;
          break;
        }

        send_status_request();
        command_state_ = CommandState::IDLE;
        log(2, "%s complete", use_register_command_ ? "Device registration" : "Registration handshake");
      }
      if (elapsed >= HANDSHAKE_TIMEOUT_MS) {
        log(0, "Handshake timeout");
        command_state_ = CommandState::IDLE;
        break;
      }
      break;

    case CommandState::HEAT_SET_TEMP:
      if (elapsed >= PRE_SETPOINT_DELAY_MS) {
        if (config_.protocol_version != 1 || pending_mode_ != MODE_MY_TEMP) {
          command_state_ = CommandState::HEAT_START;
          break;
        }

        send_set_my_temp(pending_temp_f_);
        command_state_ = CommandState::HEAT_START;
        command_state_time_ = now_ms;
      }
      break;

    case CommandState::HEAT_START:
      if (elapsed >= PRE_SETPOINT_DELAY_MS && !pending_my_temp_) {
        send_set_mode(pending_mode_, pending_temp_f_);
        const auto next_state = config_.protocol_version == 1 ? CommandState::HEAT_COMPLETE : CommandState::HEAT_POLL;
        command_state_ = next_state;
        command_state_time_ = now_ms;
      }
      break;

    case CommandState::HEAT_POLL:
      if (elapsed >= POST_SETPOINT_DELAY_MS) {
        // Proceed to control even if no status (timeout after POST_SETPOINT_DELAY_MS)
        uint8_t seq_base = (last_status_seq_ != 0) ? last_status_seq_ : last_rx_seq_;
        send_request_compact_status(seq_base);
        command_state_ = CommandState::HEAT_POLL_REPEAT;
        command_state_time_ = now_ms;
      }
      break;

    case CommandState::HEAT_POLL_REPEAT:
      if (elapsed >= CONTROL_DELAY_MS) {
        uint8_t seq_ack = next_tx_seq();
        send_request_compact_status(seq_ack);
        command_state_ = CommandState::HEAT_COMPLETE;
        command_state_time_ = now_ms;
      }
      break;

    case CommandState::HEAT_COMPLETE:
      if (elapsed >= CONTROL_DELAY_MS) {
        command_state_ = CommandState::IDLE;
        log(3, "Start heating sequence complete");
      }
      break;

    case CommandState::STOP:
      send_stop();
      command_state_ = CommandState::STOP_POLL;
      command_state_time_ = now_ms;
      break;

    case CommandState::STOP_POLL:
      if (elapsed >= CONTROL_DELAY_MS) {
        uint8_t seq_ctrl = (last_status_seq_ != 0) ? last_status_seq_ : last_rx_seq_;
        send_request_compact_status(seq_ctrl);
        command_state_ = CommandState::STOP_REPEAT;
        command_state_time_ = now_ms;
      }
      break;

    case CommandState::STOP_REPEAT:
      if (elapsed >= CONTROL_DELAY_MS) {
        send_stop();
        command_state_ = CommandState::IDLE;
        log(3, "Stop heating sequence complete");
      }
      break;
  }

  if (command_state_ != initial_state) {
    log(3, "Command state changed from %d to %d", static_cast<int>(initial_state), static_cast<int>(command_state_));
    // Recursively process state machine if state changed
    process_command_state_machine(now_ms);
  }

  if (command_state_ != CommandState::IDLE && command_state_ == initial_state && elapsed >= IDLE_TIMEOUT_MS) {
    log(0, "Idle timeout from %d to IDLE", static_cast<int>(initial_state));
    command_state_ = CommandState::IDLE;
  }
}

// ============================================================================
// State Queries
// ============================================================================

bool CosoriKettleState::can_send_command() const {
  return command_state_ == CommandState::IDLE &&
         !waiting_for_write_ack_ &&
         send_chunk_index_ >= send_total_chunks_;
}

void CosoriKettleState::track_online_status() {
  if (state_.no_response_count < NO_RESPONSE_THRESHOLD) {
    state_.no_response_count++;
  }

  if (state_.no_response_count >= NO_RESPONSE_THRESHOLD && state_.status_received) {
    log(1, "No response from kettle, marking offline");
    state_.status_received = false;
  }
}

void CosoriKettleState::reset_online_status() {
  state_.no_response_count = 0;
}

}  // namespace cosori_kettle_ble
}  // namespace esphome
