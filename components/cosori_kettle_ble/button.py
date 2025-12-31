"""Button platform for Cosori Kettle BLE."""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import button
from esphome.const import CONF_ID
from . import COSORI_KETTLE_BLE_COMPONENT_SCHEMA, CONF_COSORI_KETTLE_BLE_ID, cosori_kettle_ble_ns

CONF_REGISTER_BUTTON = "register_button"

CosoriKettleRegisterButton = cosori_kettle_ble_ns.class_("CosoriKettleRegisterButton", button.Button, cg.Component)

CONFIG_SCHEMA = COSORI_KETTLE_BLE_COMPONENT_SCHEMA.extend(
    {
        cv.Optional(CONF_REGISTER_BUTTON): button.button_schema(
            CosoriKettleRegisterButton,
        ),
    }
)


async def to_code(config):
    """Code generation for button platform."""
    parent = await cg.get_variable(config[CONF_COSORI_KETTLE_BLE_ID])

    if CONF_REGISTER_BUTTON in config:
        conf = config[CONF_REGISTER_BUTTON]
        btn = await button.new_button(conf)
        await cg.register_component(btn, conf)
        await cg.register_parented(btn, config[CONF_COSORI_KETTLE_BLE_ID])
        cg.add(parent.set_register_button(btn))
