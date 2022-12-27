"""Constants for the rfplayer integration."""
DOMAIN = "rfplayer"
DATA_RFOBJECT = "rfobject"

CONF_AUTOMATIC_ADD = "automatic_add"
CONF_RECONNECT_INTERVAL = "reconnect_interval"

DEFAULT_RECONNECT_INTERVAL = 10
DEFAULT_SIGNAL_REPETITIONS = 1

PLATFORMS = ["sensor", "switch", "number","cover"]

ATTR_EVENT = "event"

RFPLAYER_PROTOCOL = "rfplayer_protocol"

CONF_DEVICE_ADDRESS = "device_address"
CONF_FIRE_EVENT = "fire_event"
CONF_IGNORE_DEVICES = "ignore_devices"
CONF_SIGNAL_REPETITIONS = "signal_repetitions"
CONF_ENTITY_TYPE = "entity_type"
CONF_ID = "id"
CONF_PLATFORM = "platform"

DATA_DEVICE_REGISTER = "device_register"
DATA_ENTITY_LOOKUP = "entity_lookup"

CONNECTION_TIMEOUT = 10

EVENT_BUTTON_PRESSED = "button_pressed"
EVENT_KEY_COMMAND = "command"
EVENT_KEY_ID = "id"
EVENT_KEY_SENSOR = "sensor"
EVENT_KEY_COVER = "cover"
EVENT_KEY_UNIT = "unit"

RFPLAYER_GROUP_COMMANDS = ["allon", "alloff"]

SERVICE_SEND_COMMAND = "send_command"
SERVICE_DELETE = "delete"

SIGNAL_AVAILABILITY = "rfplayer_device_available"
SIGNAL_HANDLE_EVENT = "rfplayer_handle_event_{}"
SIGNAL_EVENT = "rfplayer_event"

COMMAND_ON = "ON"
COMMAND_OFF = "OFF"
COMMAND_DIM = "DIM"
COMMAND_DOWN = "DOWN"
COMMAND_UP = "UP"
COMMAND_MY = "MY"

ENTITY_TYPE_SWITCH = "switch"
ENTITY_TYPE_COVER = "cover"
ENTITY_TYPE_SENSOR = "sensor"
ENTITY_TYPE_NUMBER = "number"