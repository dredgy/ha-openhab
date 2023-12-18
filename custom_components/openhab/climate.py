from __future__ import annotations

from typing import Any


from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import DeviceEntryType

from .const import DOMAIN, VERSION, NAME
from .device_classes_map import SWITCH_DEVICE_CLASS_MAP
from .entity import OpenHABEntity

TEMPERATURE_CELSIUS = "celsius"
TEMPERATURE_FAHRENHEIT = "fahrenheit"
DEFAULT_TEMPERATURE_UNIT = TEMPERATURE_CELSIUS

from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_TEMPERATURE_UNIT,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_devices(
        OpenHABClimate(hass, coordinator, item)
        for item in coordinator.data.values()
        if item.type_ex == 'devireg_unit'
    )


class OpenHABClimate(OpenHABEntity, ClimateEntity):
    _attr_device_class_map = []

    @property
    def device_info(self) -> DeviceInfo:
        version = VERSION
        oh_version = self.coordinator.version
        if oh_version is not None:
            version = oh_version

        if self.item.devireg['thing']:
            return DeviceInfo(
                identifiers={(f"{DOMAIN}_{self.item.devireg['name_id']}", self._host)},
                name =self.item.devireg['thing']['label'],
                model         = self.item.devireg['thing']['properties']['regulationType'],
                manufacturer  = 'Devireg',
                sw_version    = self.item.devireg['thing']['properties']['firmwareVersion'],
                serial_number = self.item.devireg['thing']['properties']['serialNumber'],
                configuration_url=self._base_url
            )
        else:
            return DeviceInfo(
                identifiers={(f"{DOMAIN}_{self.item.devireg['name_id']}", self._host)},
                name = self.item.label,
                model=version,
                manufacturer  = 'Devireg',
                configuration_url=self._base_url
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        name = self.item.name
        label = self.item.label
        api_link = f"{self._base_url}/rest/items/{name}"
        ui_link = f"{self._base_url}/settings/items/{name}"
        is_group = bool(self.item.group)
        #attributes3 = self.item.devireg['attrs']

        attributes = {
            "category": self.item.category,
            "editable": self.item.editable,
            "group_names": self.item.groupNames,
            "hostname": self._host,
            "id": f"{DOMAIN}_{name}",
            "integration": DOMAIN,
            "is_group": self.item.group,
            "label": label,
            "api_link": api_link,
            "main_ui_link": ui_link,
            "name": self.item.name,
            "tags": self.item.tags,
            "type": self.item.type_,
            "raw_state": self.item._raw_state,
            "unit_of_measure": str(self.item.unit_of_measure),
        }
        #if is_group and len(self.item.members):
        #    attributes["members"] = self.item.members.keys()

        if self.item.quantityType is not None:
            attributes["quantity_type"] = self.item.quantityType

        return self.item.devireg
    @property
    def supported_features(self):
        """Flag supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        s = self.item.devireg['attrs']['State']['value']
        if s=='OFF':
            return HVACMode.OFF
        else:
            return HVACMode.HEAT

    @property
    def hvac_modes(self):
        return [HVACMode.HEAT, HVACMode.OFF]

    @property
    def preset_mode(self):
        for m in self.item.devireg['attrs']['Mode']['options']:
            if m['value']==self.item.devireg['attrs']['Mode']['value']:
                return m['label']

        #return self.item.devireg['attrs']['Mode']['value']

    @property
    def preset_modes(self):
        modes = []
        for m in self.item.devireg['attrs']['Mode']['options']:
            modes.append(m['label'])

        return modes

    @property
    def current_temperature(self):
        """Return the current temperature."""
        if self.item.devireg['thing']:
            is_floor = self.item.devireg['thing']['properties']['regulationType']=='Floor'
        else:
            is_floor = False

        if is_floor:
            return self.item.devireg['attrs']['Floor_temperature']['value']
        else:
            return self.item.devireg['attrs']['Room_temperature']['value']

    def target_temp_variable_by_state(self):
        s = self.item.devireg['attrs']['State']['value']
        if s=='AWAY':
            t= 'Away'
        elif s=='VACATION':
            t='Vacation'
        elif s=='MANUAL':
            t='Manual'
        elif s=='OVERRIDE' or s=='HOME':
            t='At_Home'
        else:
            t='Frost_protection'

        return f"{t}_temperature"

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self.item.devireg['attrs'][self.target_temp_variable_by_state()]['value']

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self.item.devireg['attrs']['Away_temperature']['step']

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode==HVACMode.OFF:
            mode = 'Off'
        else:
            mode = 'Schedule'

        await self.hass.async_add_executor_job(
            self.coordinator.api.openhab.req_post,
                f"/items/{self._id}_Mode",
                str(mode),
        )

        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode):
        if not self.item:
            return

        mode = False
        for m in self.item.devireg['attrs']['Mode']['options']:
            if m['label']==preset_mode:
                mode = m['value']

        if mode:
            await self.hass.async_add_executor_job(
                self.coordinator.api.openhab.req_post,
                f"/items/{self._id}_Mode",
                str(mode),
            )

            await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if not self.item:
            return

        target_temp = self.target_temp_variable_by_state()

        await self.hass.async_add_executor_job(
            self.coordinator.api.openhab.req_post,
                f"/items/{self._id}_{target_temp}",
                str(kwargs['temperature'])
            )
        await self.coordinator.async_request_refresh()