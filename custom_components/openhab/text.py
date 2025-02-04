"""Text platform for openHAB."""
from __future__ import annotations

from typing import Any

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import OpenHABEntity
TEXT_MAX_LENGTH = 255

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Setup text platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_devices(
        OpenHABText(hass, coordinator, item)
        for item in coordinator.data.values()
        if item.type_ == "String"
    )


class OpenHABText(OpenHABEntity, TextEntity):
    """openHAB text class."""

    _attr_device_class_map = []

    @property
    def native_max(self) -> int:
        """Return the maximum length of text."""
        return TEXT_MAX_LENGTH  # No maximum length

    async def async_set_value(self, value: str) -> None:
        """Set new value."""
        await self.hass.async_add_executor_job(self.item.command, value)
        await self.coordinator.async_request_refresh()

    @property
    def native_value(self) -> str:
        """Return the current value."""
        state = self.item._state
        if state is None:
            return ""

        # For JSON-like strings that are too long, return a descriptive message
        if len(str(state)) > TEXT_MAX_LENGTH and any(identifier in self.item.name.lower() for identifier in ['json', 'array', 'list']):
            return "JSON Data Received"

        return str(state)