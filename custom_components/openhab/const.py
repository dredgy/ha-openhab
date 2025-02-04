"""Constants for openHAB."""
from datetime import timedelta
from logging import Logger, getLogger

# Base component constants
NAME = "openHAB"
DOMAIN = "openhab"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ATTRIBUTION = "Data provided by openHAB REST API"
ISSUE_URL = "https://github.com/dredgy/ha-openhab/issues"
DATA_COORDINATOR_UPDATE_INTERVAL = timedelta(seconds=1)
LOGGER: Logger = getLogger(__package__)

# Platforms
BINARY_SENSOR = "binary_sensor"
CAMERA = "camera"
COVER = "cover"
DEVICE_TRACKER = "device_tracker"
LIGHT = "light"
MEDIA_PLAYER = "media_player"
SENSOR = "sensor"
SWITCH = "switch"
CLIMATE = "climate"
TEXT = "text"
PLATFORMS = [BINARY_SENSOR, COVER, DEVICE_TRACKER, LIGHT, MEDIA_PLAYER, SWITCH, CLIMATE, TEXT, CAMERA]


# Configuration and options
CONF_ENABLED = "enabled"
CONF_BASE_URL = "base_url"
CONF_AUTH_TYPE = "auth_type"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_AUTH_TOKEN = "auth_token"
CONF_AUTH_TYPE_BASIC = "OAuth2"
CONF_AUTH_TYPE_TOKEN = "token"

AUTH_TYPES = [CONF_AUTH_TYPE_BASIC, CONF_AUTH_TYPE_TOKEN]

# Defaults
DEFAULT_NAME = DOMAIN

ITEMS_MAP = {
    BINARY_SENSOR: ["Contact"],
    CAMERA: ["Image"],
    COVER: ["Rollershutter"],
    DEVICE_TRACKER: ["Location"],
    LIGHT: ["Color", "Dimmer"],
    MEDIA_PLAYER: ["Player"],
    SENSOR: [
        "DateTime",
        "Number",
        "Number:Length",
        "Number:Temperature",
        "Number:Pressure",
        "Number:Speed",
        "Number:Intensity",
        "Number:Dimensionless",
        "Number:Angle",
        "String",
    ],
    SWITCH: ["Switch"],
    CLIMATE: ["Climate"]
}

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
