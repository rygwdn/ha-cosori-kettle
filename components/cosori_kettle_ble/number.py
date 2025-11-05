"""Number platform for Cosori Kettle BLE."""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import number
from esphome.const import CONF_ID, UNIT_FAHRENHEIT
from . import COSORI_KETTLE_BLE_COMPONENT_SCHEMA, CONF_COSORI_KETTLE_BLE_ID, cosori_kettle_ble_ns

CONF_TARGET_SETPOINT = "target_setpoint"

CosoriKettleNumber = cosori_kettle_ble_ns.class_("CosoriKettleNumber", number.Number, cg.Component)

CONFIG_SCHEMA = COSORI_KETTLE_BLE_COMPONENT_SCHEMA.extend(
    {
        cv.Optional(CONF_TARGET_SETPOINT): number.NUMBER_SCHEMA.extend(
            {
                cv.GenerateID(): cv.declare_id(CosoriKettleNumber),
                cv.Optional("min_value", default=104): cv.float_,
                cv.Optional("max_value", default=212): cv.float_,
                cv.Optional("step", default=1): cv.float_,
                cv.Optional("unit_of_measurement", default=UNIT_FAHRENHEIT): cv.string,
            }
        ).extend(cv.COMPONENT_SCHEMA),
    }
)


async def to_code(config):
    """Code generation for number platform."""
    parent = await cg.get_variable(config[CONF_COSORI_KETTLE_BLE_ID])

    if CONF_TARGET_SETPOINT in config:
        conf = config[CONF_TARGET_SETPOINT]
        num = cg.new_Pvariable(conf[CONF_ID])
        await number.register_number(
            num,
            conf,
            min_value=conf["min_value"],
            max_value=conf["max_value"],
            step=conf["step"],
        )
        await cg.register_component(num, conf)
        cg.add(num.set_parent(parent))
        cg.add(parent.set_target_setpoint_number(num))
