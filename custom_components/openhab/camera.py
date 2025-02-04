"""Camera platform for openHAB."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.components.camera import CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import OpenHABEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up camera platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug(f"Available items: {coordinator.data.values()}")

    async_add_devices(
        OpenHABCamera(hass, coordinator, item)
        for item in coordinator.data.values()
        if item.type_ == "Image"
    )


class OpenHABCamera(OpenHABEntity, Camera):
    """OpenHAB Camera class."""
    _attr_device_class_map = []

    def __init__(self, hass, coordinator, item) -> None:
        """Initialize the camera."""
        OpenHABEntity.__init__(self, hass, coordinator, item)
        Camera.__init__(self)
        self._attr_is_streaming = False

        # Store the OpenHAB API client
        self._api = coordinator.api

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return image response."""
        try:
            # Fetch the image directly from OpenHAB using the API
            _LOGGER.debug(f"Attempting to fetch image for item: {self.item.name}")

            image_bytes = await self._api.async_get_item_image(self.item.name)

            if not image_bytes:
                _LOGGER.warning(f"No image data found for {self.item.name}")
                return None

            return image_bytes

        except Exception as err:
            _LOGGER.error(f"Error getting camera image for {self.item.name}: {err}")
            return None

    @property
    def supported_features(self) -> CameraEntityFeature:
        """Return supported features."""
        return CameraEntityFeature(0)

    @property
    def device_class_map(self):
        """Camera entities don't use the standard device class map."""
        return []