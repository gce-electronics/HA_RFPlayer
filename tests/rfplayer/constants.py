SOME_PROTOCOLS = ["X2D", "RTS"]

# Jamming examples
# ===============

JAMMING_BINARY_SENSOR_ENTITY_ID = "binary_sensor.jamming_0_detector"
JAMMING_ID_STRING = "JAMMING_0"
JAMMING_BINARY_SENSOR_FRIENDLY_NAME = "JAMMING 0 Detector"

# Oregon examples
# ===============

OREGON_ADDRESS = "39168"
OREGON_REDIRECT_ADDRESS = "49168"
OREGON_EVENT_DATA = {
    "frame": {
        "header": {
            "frameType": "0",
            "dataFlag": "0",
            "rfLevel": "-71",
            "floorNoise": "-98",
            "rfQuality": "5",
            "protocol": "5",
            "protocolMeaning": "OREGON",
            "infoType": "9",
            "frequency": "433920",
        },
        "infos": {
            "subType": "0",
            "id_PHY": "0x2A19",
            "id_PHYMeaning": "PCR800",
            "adr_channel": OREGON_ADDRESS,
            "adr": "153",
            "channel": "0",
            "qualifier": "48",
            "lowBatt": "0",
            "measures": [
                {"type": "total rain", "value": "1040.1", "unit": "mm"},
                {
                    "type": "current rain",
                    "value": "0.00",
                    "unit": "mm/h",
                },
            ],
        },
    }
}


OREGON_ID_STRING = f"OREGON-{OREGON_ADDRESS}"
OREGON_DEVICE_INFO = {"protocol": "OREGON", "address": OREGON_ADDRESS, "profile_name": "Oregon Rain Sensor"}
OREGON_BINARY_SENSOR_ENTITY_ID = f"binary_sensor.oregon_{OREGON_ADDRESS}_low_battery"
OREGON_BINARY_SENSOR_FRIENDLY_NAME = f"OREGON {OREGON_ADDRESS} Low Battery"
OREGON_BINARY_SENSOR_STATE = "off"
OREGON_RAIN_SENSOR_ENTITY_ID = f"sensor.oregon_{OREGON_ADDRESS}_total_rain"
OREGON_RAIN_SENSOR_FRIENDLY_NAME = f"OREGON {OREGON_ADDRESS} Total Rain"
OREGON_RAIN_SENSOR_STATE = "1040.1"
OREGON_RFLEVEL_SENSOR_ENTITY_ID = f"sensor.oregon_{OREGON_ADDRESS}_rf_level"
OREGON_RFLEVEL_SENSOR_FRIENDLY_NAME = f"OREGON {OREGON_ADDRESS} Rf Level"
OREGON_RFLEVEL_SENSOR_STATE = "-71.0"

# Blyss examples
# ===============

BLYSS_ADDRESS = "4261483730"
BLYSS_OFF_EVENT_DATA = {
    "frame": {
        "header": {
            "frameType": "0",
            "dataFlag": "0",
            "rfLevel": "-41",
            "floorNoise": "-97",
            "rfQuality": "10",
            "protocol": "3",
            "protocolMeaning": "BLYSS",
            "infoType": "1",
            "frequency": "433920",
        },
        "infos": {
            "subType": "0",
            "id": BLYSS_ADDRESS,
            "subTypeMeaning": "OFF",
        },
    }
}
BLYSS_ALL_ON_EVENT_DATA = {
    "frame": {
        "header": {
            "frameType": "0",
            "dataFlag": "0",
            "rfLevel": "-41",
            "floorNoise": "-97",
            "rfQuality": "10",
            "protocol": "3",
            "protocolMeaning": "BLYSS",
            "infoType": "1",
            "frequency": "433920",
        },
        "infos": {
            "subType": "5",
            "id": BLYSS_ADDRESS,
            "subTypeMeaning": "ALL_OFF",
        },
    }
}
BLYSS_ID_STRING = f"BLYSS-{BLYSS_ADDRESS}"


BLYSS_MOTION_ADDRESS = "4261583730"
BLYSS_MOTION_ID_STRING = f"BLYSS-{BLYSS_MOTION_ADDRESS}"
BLYSS_MOTION_DEVICE_INFO = {
    "protocol": "BLYSS",
    "address": BLYSS_MOTION_ADDRESS,
    "profile_name": "X10|CHACON|KD101|BLYSS|FS20 Motion detector",
}
BLYSS_BINARY_SENSOR_MOTION_ENTITY_ID = f"binary_sensor.blyss_{BLYSS_MOTION_ADDRESS}_motion"
BLYSS_BINARY_SENSOR_MOTION_FRIENDLY_NAME = f"BLYSS {BLYSS_MOTION_ADDRESS} Motion"

BLYSS_SMOKE_ADDRESS = "4261683730"
BLYSS_SMOKE_ID_STRING = f"BLYSS-{BLYSS_SMOKE_ADDRESS}"
BLYSS_SMOKE_DEVICE_INFO = {
    "protocol": "BLYSS",
    "address": BLYSS_SMOKE_ADDRESS,
    "profile_name": "X10|CHACON|KD101|BLYSS|FS20 Smoke detector",
}
BLYSS_BINARY_SENSOR_SMOKE_ENTITY_ID = f"binary_sensor.blyss_{BLYSS_SMOKE_ADDRESS}_smoke"
BLYSS_BINARY_SENSOR_SMOKE_FRIENDLY_NAME = f"BLYSS {BLYSS_SMOKE_ADDRESS} Smoke"

# CHACON Examples
# ===============

CHACON_ADDRESS = "146139014"
CHACON_UNIT_CODE = "6"
CHACON_ON_EVENT_DATA = {
    "frame": {
        "header": {
            "frameType": "0",
            "dataFlag": "0",
            "rfLevel": "-41",
            "floorNoise": "-97",
            "rfQuality": "10",
            "protocol": "4",
            "protocolMeaning": "CHACON",
            "infoType": "1",
            "frequency": "433920",
        },
        "infos": {
            "subType": "1",
            "id": CHACON_ADDRESS,
            "subTypeMeaning": "ON",
        },
    }
}
CHACON_GROUP_ADDRESS = "146139008"
CHACON_ALL_ON_EVENT_DATA = {
    "frame": {
        "header": {
            "frameType": "0",
            "dataFlag": "0",
            "rfLevel": "-41",
            "floorNoise": "-97",
            "rfQuality": "10",
            "protocol": "4",
            "protocolMeaning": "CHACON",
            "infoType": "1",
            "frequency": "433920",
        },
        "infos": {
            "subType": "5",
            "id": CHACON_GROUP_ADDRESS,
            "subTypeMeaning": "ALL_ON",
        },
    }
}

CHACON_ID_STRING = f"CHACON-{CHACON_ADDRESS}"
CHACON_BINARY_SENSOR_ENTITY_ID = f"binary_sensor.chacon_{CHACON_ADDRESS}_status"
CHACON_BINARY_SENSOR_FRIENDLY_NAME = f"CHACON {CHACON_ADDRESS} Status"
CHACON_BINARY_SENSOR_DEVICE_INFO = {
    "protocol": "CHACON",
    "address": CHACON_ADDRESS,
    "profile_name": "X10|CHACON|KD101|BLYSS|FS20 On/Off",
}
CHACON_LIGHT_ENTITY_ID = f"light.chacon_{CHACON_ADDRESS}_light"
CHACON_LIGHT_FRIENDLY_NAME = f"CHACON {CHACON_ADDRESS} Light"
CHACON_LIGHT_DEVICE_INFO = {
    "protocol": "CHACON",
    "address": CHACON_ADDRESS,
    "profile_name": "X10|CHACON|KD101|BLYSS|FS20 Lighting",
}
CHACON_SWITCH_ENTITY_ID = f"switch.chacon_{CHACON_ADDRESS}_switch"
CHACON_SWITCH_FRIENDLY_NAME = f"CHACON {CHACON_ADDRESS} Switch"
CHACON_SWITCH_DEVICE_INFO = {
    "protocol": "CHACON",
    "address": CHACON_ADDRESS,
    "profile_name": "X10|CHACON|KD101|BLYSS|FS20 Switch",
}

# X2D Examples
# ===============

X2D_UNIT_CODE = "1"
X2D_ADDRESS = "2095907073"
X2D_ON_EVENT_DATA = {
    "frame": {
        "header": {
            "frameType": "0",
            "dataFlag": "0",
            "rfLevel": "-41",
            "floorNoise": "-97",
            "rfQuality": "10",
            "protocol": "1",
            "protocolMeaning": "X2D",
            "infoType": "10",
            "frequency": "433920",
        },
        "infos": {
            "subType": "1",
            "id": X2D_ADDRESS,
            "subTypeMeaning": "DELTA 200",
            "qualifier": "0",
            "function": "1",
            "functionMeaning": "HEATING_SPEED",
            "state": "1",
            "stateMeaning": "ON",
        },
    }
}
X2D_COMFORT_EVENT_DATA = {
    "frame": {
        "header": {
            "frameType": "0",
            "dataFlag": "0",
            "rfLevel": "-41",
            "floorNoise": "-97",
            "rfQuality": "10",
            "protocol": "1",
            "protocolMeaning": "X2D",
            "infoType": "0",
            "frequency": "433920",
        },
        "infos": {
            "subType": "1",
            "id": X2D_ADDRESS,
            "subTypeMeaning": "DELTA 200",
            "qualifier": "0",
            "function": "2",
            "functionMeaning": "OPERATING_MODE",
            "state": "3",
            "stateMeaning": "COMFORT",
        },
    }
}

X2D_ID_STRING = f"X2D-{X2D_ADDRESS}"
X2D_ENTITY_ID = f"climate.x2d_{X2D_ADDRESS}_thermostat"
X2D_FRIENDLY_NAME = f"X2D {X2D_ADDRESS} Thermostat"
X2D_DEVICE_INFO = {
    "protocol": "X2D",
    "address": X2D_ADDRESS,
    "profile_name": "X2D Thermostat Elec",
}
X2D_PRESET_MODE = "Comfort"


# RTS Examples
# ===============

RTS_ADDRESS = "123"
RTS_UNIT_CODE = "11"
RTS_DOWN_EVENT_DATA = {
    "frame": {
        "header": {
            "frameType": "0",
            "dataFlag": "0",
            "rfLevel": "-41",
            "floorNoise": "-97",
            "rfQuality": "10",
            "protocol": "9",
            "protocolMeaning": "RTS",
            "infoType": "3",
            "frequency": "433920",
        },
        "infos": {
            "subType": "0",
            "id": RTS_ADDRESS,
            "subTypeMeaning": "SHUTTER",
            "qualifier": "1",
            "qualifierMeaning": ["Down"],
        },
    }
}
RTS_ID_STRING = f"RTS-{RTS_ADDRESS}"
RTS_ENTITY_ID = f"cover.rts_{RTS_ADDRESS}_shutter"
RTS_FRIENDLY_NAME = f"RTS {RTS_ADDRESS} Shutter"
RTS_DEVICE_INFO = {
    "protocol": "RTS",
    "address": RTS_ADDRESS,
    "profile_name": "RTS Shutter",
}
