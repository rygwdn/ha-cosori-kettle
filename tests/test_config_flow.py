"""Tests for the config_flow module."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant import data_entry_flow
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResultType

from custom_components.cosori_kettle_ble.const import CONF_DEVICE_ID, CONF_REGISTRATION_KEY, SERVICE_UUID
from custom_components.cosori_kettle_ble.config_flow import CosoriKettleConfigFlow


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_bluetooth_service_info():
    """Create a mock BluetoothServiceInfoBleak object."""
    info = MagicMock()
    info.address = "AA:BB:CC:DD:EE:FF"
    info.name = "Cosori Kettle"
    info.service_uuids = [SERVICE_UUID]
    return info


@pytest.fixture
def mock_config_flow(mock_hass):
    """Create a config flow instance."""
    flow = CosoriKettleConfigFlow()
    flow.hass = mock_hass
    return flow


class TestAsyncStepUser:
    """Test the async_step_user method."""

    @pytest.mark.asyncio
    async def test_no_devices_found(self, mock_config_flow):
        """Test when no Cosori kettles are discovered."""
        with patch(
            "custom_components.cosori_kettle_ble.config_flow.bluetooth.async_discovered_service_info"
        ) as mock_discover:
            mock_discover.return_value = []

            result = await mock_config_flow.async_step_user(user_input=None)

            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "no_devices_found"

    @pytest.mark.asyncio
    async def test_devices_discovered(self, mock_config_flow, mock_bluetooth_service_info):
        """Test when valid Cosori kettles are found."""
        with patch(
            "custom_components.cosori_kettle_ble.config_flow.bluetooth.async_discovered_service_info"
        ) as mock_discover:
            mock_discover.return_value = [mock_bluetooth_service_info]

            result = await mock_config_flow.async_step_user(user_input=None)

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            assert CONF_ADDRESS in result["data_schema"].schema

    @pytest.mark.asyncio
    async def test_filter_already_configured(self, mock_config_flow, mock_bluetooth_service_info):
        """Test that already configured devices are filtered out."""
        with patch(
            "custom_components.cosori_kettle_ble.config_flow.bluetooth.async_discovered_service_info"
        ) as mock_discover, \
        patch.object(
            mock_config_flow, "_async_current_ids", return_value={mock_bluetooth_service_info.address}
        ):
            mock_discover.return_value = [mock_bluetooth_service_info]

            result = await mock_config_flow.async_step_user(user_input=None)

            # Device should be filtered out, so no devices found
            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "no_devices_found"

    @pytest.mark.asyncio
    async def test_service_uuid_filtering(self, mock_config_flow):
        """Test that only devices with matching SERVICE_UUID are included."""
        # Create one device with correct UUID and one without
        correct_device = MagicMock()
        correct_device.address = "AA:BB:CC:DD:EE:FF"
        correct_device.name = "Cosori Kettle"
        correct_device.service_uuids = [SERVICE_UUID]

        wrong_device = MagicMock()
        wrong_device.address = "11:22:33:44:55:66"
        wrong_device.name = "Other Device"
        wrong_device.service_uuids = ["00001234-0000-1000-8000-00805f9b34fb"]

        with patch(
            "custom_components.cosori_kettle_ble.config_flow.bluetooth.async_discovered_service_info"
        ) as mock_discover:
            mock_discover.return_value = [correct_device, wrong_device]

            result = await mock_config_flow.async_step_user(user_input=None)

            assert result["type"] == FlowResultType.FORM
            # Only the correct device should be in the discovered devices
            assert len(mock_config_flow._discovered_devices) == 1
            assert correct_device.address in mock_config_flow._discovered_devices

    @pytest.mark.asyncio
    async def test_service_uuid_case_insensitive(self, mock_config_flow):
        """Test that SERVICE_UUID matching is case insensitive."""
        device = MagicMock()
        device.address = "AA:BB:CC:DD:EE:FF"
        device.name = "Cosori Kettle"
        device.service_uuids = [SERVICE_UUID.upper()]  # Use uppercase version

        with patch(
            "custom_components.cosori_kettle_ble.config_flow.bluetooth.async_discovered_service_info"
        ) as mock_discover:
            mock_discover.return_value = [device]

            result = await mock_config_flow.async_step_user(user_input=None)

            assert result["type"] == FlowResultType.FORM
            assert len(mock_config_flow._discovered_devices) == 1

    @pytest.mark.asyncio
    async def test_user_selection(self, mock_config_flow, mock_bluetooth_service_info):
        """Test when user selects a device from the form."""
        # First, populate the discovered devices
        mock_config_flow._discovered_devices = {
            mock_bluetooth_service_info.address: mock_bluetooth_service_info
        }

        user_input = {CONF_ADDRESS: mock_bluetooth_service_info.address}

        with patch.object(
            mock_config_flow, "async_set_unique_id", new_callable=AsyncMock
        ) as mock_set_unique_id, \
        patch.object(
            mock_config_flow, "_abort_if_unique_id_configured"
        ) as mock_abort, \
        patch.object(
            mock_config_flow, "async_step_pairing_mode", new_callable=AsyncMock
        ) as mock_pairing_mode:
            mock_pairing_mode.return_value = {"type": FlowResultType.FORM}

            result = await mock_config_flow.async_step_user(user_input=user_input)

            # Verify unique ID was set
            mock_set_unique_id.assert_called_once_with(
                mock_bluetooth_service_info.address, raise_on_progress=False
            )

            # Verify abort check was called
            mock_abort.assert_called_once()

            # Verify discovery info and address were stored
            assert mock_config_flow._discovery_info == mock_bluetooth_service_info
            assert mock_config_flow._selected_address == mock_bluetooth_service_info.address

            # Verify flow proceeded to pairing mode
            mock_pairing_mode.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_devices_discovered(self, mock_config_flow):
        """Test when multiple Cosori kettles are found."""
        device1 = MagicMock()
        device1.address = "AA:BB:CC:DD:EE:FF"
        device1.name = "Cosori Kettle 1"
        device1.service_uuids = [SERVICE_UUID]

        device2 = MagicMock()
        device2.address = "11:22:33:44:55:66"
        device2.name = "Cosori Kettle 2"
        device2.service_uuids = [SERVICE_UUID]

        with patch(
            "custom_components.cosori_kettle_ble.config_flow.bluetooth.async_discovered_service_info"
        ) as mock_discover:
            mock_discover.return_value = [device1, device2]

            result = await mock_config_flow.async_step_user(user_input=None)

            assert result["type"] == FlowResultType.FORM
            assert len(mock_config_flow._discovered_devices) == 2
            assert device1.address in mock_config_flow._discovered_devices
            assert device2.address in mock_config_flow._discovered_devices

    @pytest.mark.asyncio
    async def test_device_without_name(self, mock_config_flow):
        """Test handling of device without a name."""
        device = MagicMock()
        device.address = "AA:BB:CC:DD:EE:FF"
        device.name = None  # No name
        device.service_uuids = [SERVICE_UUID]

        with patch(
            "custom_components.cosori_kettle_ble.config_flow.bluetooth.async_discovered_service_info"
        ) as mock_discover:
            mock_discover.return_value = [device]

            result = await mock_config_flow.async_step_user(user_input=None)

            assert result["type"] == FlowResultType.FORM
            # The form should show "Cosori Kettle" as fallback name
            assert len(mock_config_flow._discovered_devices) == 1


class TestReauth:
    """Test the reauthentication flow."""

    @pytest.mark.asyncio
    async def test_reauth_shows_confirm_form(self, mock_config_flow):
        """Test that reauth step shows a confirmation form."""
        mock_entry = MagicMock()
        mock_entry.data = {
            CONF_DEVICE_ID: "AA:BB:CC:DD:EE:FF",
            CONF_REGISTRATION_KEY: "deadbeef" * 4,
        }
        mock_config_flow.hass.config_entries.async_get_entry.return_value = mock_entry
        mock_config_flow.context = {"entry_id": "test_entry_id"}

        result = await mock_config_flow.async_step_reauth(mock_entry.data)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

    @pytest.mark.asyncio
    async def test_reauth_confirm_proceeds_to_pairing(self, mock_config_flow):
        """Test that confirming reauth proceeds to pairing mode selection."""
        mock_entry = MagicMock()
        mock_entry.data = {CONF_DEVICE_ID: "AA:BB:CC:DD:EE:FF"}
        mock_config_flow._update_entry = mock_entry
        mock_config_flow._selected_address = "AA:BB:CC:DD:EE:FF"

        with patch.object(
            mock_config_flow, "async_step_pairing_mode", new_callable=AsyncMock
        ) as mock_pairing:
            mock_pairing.return_value = {"type": FlowResultType.FORM, "step_id": "pairing_mode"}
            result = await mock_config_flow.async_step_reauth_confirm(user_input={})

        mock_pairing.assert_called_once()

    @pytest.mark.asyncio
    async def test_reauth_updates_entry_on_success(self, mock_config_flow):
        """Test that successful reauth updates the config entry."""
        mock_entry = MagicMock()
        mock_entry.data = {CONF_DEVICE_ID: "AA:BB:CC:DD:EE:FF"}
        mock_config_flow._update_entry = mock_entry
        mock_config_flow._selected_address = "AA:BB:CC:DD:EE:FF"
        mock_config_flow._discovery_info = None

        new_key = "ab" * 16
        mock_ble_device = MagicMock()

        with patch(
            "custom_components.cosori_kettle_ble.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ), patch(
            "custom_components.cosori_kettle_ble.config_flow.CosoriKettle"
        ) as mock_kettle_cls, patch.object(
            mock_config_flow, "async_update_reload_and_abort"
        ) as mock_update:
            mock_kettle = AsyncMock()
            mock_kettle_cls.return_value.__aenter__ = AsyncMock(return_value=mock_kettle)
            mock_kettle_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_update.return_value = {"type": FlowResultType.ABORT, "reason": "reauth_successful"}

            await mock_config_flow.async_step_enter_key(
                user_input={"registration_key": new_key}
            )

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args
        assert call_kwargs[1]["data_updates"][CONF_REGISTRATION_KEY] == new_key


class TestReconfigure:
    """Test the reconfigure flow."""

    @pytest.mark.asyncio
    async def test_reconfigure_sets_address_and_proceeds(self, mock_config_flow):
        """Test that reconfigure sets the address from the existing entry."""
        mock_entry = MagicMock()
        mock_entry.data = {CONF_DEVICE_ID: "AA:BB:CC:DD:EE:FF"}

        with patch.object(
            mock_config_flow, "_get_reconfigure_entry", return_value=mock_entry
        ), patch.object(
            mock_config_flow, "async_step_pairing_mode", new_callable=AsyncMock
        ) as mock_pairing:
            mock_pairing.return_value = {"type": FlowResultType.FORM, "step_id": "pairing_mode"}
            await mock_config_flow.async_step_reconfigure()

        assert mock_config_flow._selected_address == "AA:BB:CC:DD:EE:FF"
        assert mock_config_flow._update_entry is mock_entry
        mock_pairing.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconfigure_updates_entry_on_pair(self, mock_config_flow):
        """Test that successful pairing during reconfigure updates the config entry."""
        mock_entry = MagicMock()
        mock_entry.data = {CONF_DEVICE_ID: "AA:BB:CC:DD:EE:FF"}
        mock_config_flow._update_entry = mock_entry
        mock_config_flow._selected_address = "AA:BB:CC:DD:EE:FF"
        mock_config_flow._discovery_info = None

        mock_ble_device = MagicMock()

        with patch(
            "custom_components.cosori_kettle_ble.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ), patch(
            "custom_components.cosori_kettle_ble.config_flow.CosoriKettle"
        ) as mock_kettle_cls, patch.object(
            mock_config_flow, "async_update_reload_and_abort"
        ) as mock_update:
            mock_kettle = AsyncMock()
            mock_kettle_cls.return_value.__aenter__ = AsyncMock(return_value=mock_kettle)
            mock_kettle_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_kettle.pair = AsyncMock()
            mock_update.return_value = {"type": FlowResultType.ABORT, "reason": "reauth_successful"}

            await mock_config_flow.async_step_pair_device(user_input={})

        mock_update.assert_called_once()
        assert CONF_REGISTRATION_KEY in mock_update.call_args[1]["data_updates"]
