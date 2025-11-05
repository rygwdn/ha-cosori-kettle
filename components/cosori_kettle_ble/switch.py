"""Switch platform for Cosori Kettle BLE."""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import switch
from esphome.const import CONF_ID
from . import COSORI_KETTLE_BLE_COMPONENT_SCHEMA, CONF_COSORI_KETTLE_BLE_ID, cosori_kettle_ble_ns

CONF_HEATING_SWITCH = "heating_switch"
CONF_BLE_CONNECTION_SWITCH = "ble_connection_switch"

CosoriKettleHeatingSwitch = cosori_kettle_ble_ns.class_("CosoriKettleHeatingSwitch", switch.Switch, cg.Component)
CosoriKettleBLEConnectionSwitch = cosori_kettle_ble_ns.class_("CosoriKettleBLEConnectionSwitch", switch.Switch, cg.Component)

CONFIG_SCHEMA = COSORI_KETTLE_BLE_COMPONENT_SCHEMA.extend(
    {
        cv.Optional(CONF_HEATING_SWITCH): switch.SWITCH_SCHEMA.extend(
            {
                cv.GenerateID(): cv.declare_id(CosoriKettleHeatingSwitch),
            }
        ).extend(cv.COMPONENT_SCHEMA),
        cv.Optional(CONF_BLE_CONNECTION_SWITCH): switch.SWITCH_SCHEMA.extend(
            {
                cv.GenerateID(): cv.declare_id(CosoriKettleBLEConnectionSwitch),
            }
        ).extend(cv.COMPONENT_SCHEMA),
    }
)


async def to_code(config):
    """Code generation for switch platform."""
    parent = await cg.get_variable(config[CONF_COSORI_KETTLE_BLE_ID])

    if CONF_HEATING_SWITCH in config:
        conf = config[CONF_HEATING_SWITCH]
        sw = cg.new_Pvariable(conf[CONF_ID])
        await switch.register_switch(sw, conf)
        await cg.register_component(sw, conf)
        cg.add(sw.set_parent(parent))
        cg.add(parent.set_heating_switch(sw))

    if CONF_BLE_CONNECTION_SWITCH in config:
        conf = config[CONF_BLE_CONNECTION_SWITCH]
        sw = cg.new_Pvariable(conf[CONF_ID])
        await switch.register_switch(sw, conf)
        await cg.register_component(sw, conf)
        cg.add(sw.set_parent(parent))
        cg.add(parent.set_ble_connection_switch(sw))
