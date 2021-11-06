"""Constants for the rfplayer integration."""
DOMAIN = "rfplayer"
DATA_RFOBJECT = "rfobject"

CONF_AUTOMATIC_ADD = "automatic_add"
CONF_WAIT_FOR_ACK = "wait_for_ack"
CONF_RECONNECT_INTERVAL = "reconnect_interval"

DEFAULT_RECONNECT_INTERVAL = 10
DEFAULT_SIGNAL_REPETITIONS = 1

PLATFORMS = ["sensor"]

ATTR_EVENT = "event"
ATTR_STATE = "state"

CONF_ALIASES = "aliases"
CONF_GROUP_ALIASES = "group_aliases"
CONF_GROUP = "group"
CONF_NOGROUP_ALIASES = "nogroup_aliases"
CONF_DEVICE_DEFAULTS = "device_defaults"
CONF_DEVICE_ID = "device_id"
CONF_FIRE_EVENT = "fire_event"
CONF_IGNORE_DEVICES = "ignore_devices"
CONF_SIGNAL_REPETITIONS = "signal_repetitions"

DATA_DEVICE_REGISTER = "rfplayer_device_register"
DATA_ENTITY_LOOKUP = "rfplayer_entity_lookup"
DATA_ENTITY_GROUP_LOOKUP = "rfplayer_entity_group_only_lookup"

CONNECTION_TIMEOUT = 10

EVENT_BUTTON_PRESSED = "button_pressed"
EVENT_KEY_COMMAND = "command"
EVENT_KEY_ID = "id"
EVENT_KEY_SENSOR = "sensor"
EVENT_KEY_UNIT = "unit"

RFPLAYER_GROUP_COMMANDS = ["allon", "alloff"]

SERVICE_SEND_COMMAND = "send_command"

SIGNAL_AVAILABILITY = "rfplayer_device_available"
SIGNAL_HANDLE_EVENT = "rfplayer_handle_event_{}"
SIGNAL_EVENT = "rfplayer_event"

TMP_ENTITY = "tmp.{}"
