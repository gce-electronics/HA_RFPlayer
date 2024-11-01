# RfPlayer HomeAssistant Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![Community Forum][forum-shield]][forum]

_Integration to integrate with [GCE RfPlayer][rfplayer]._

**This integration will set up the following platforms.**

Platforms:

- `binary_sensor`
- `sensor`
- `light`
- `climate`

Services:

- `send command`
- `simulate event`

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gce-electronics&repository=HA_RFPlayer&category=integration)

### Manually

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `rfplayer`.
1. Download _all_ the files from the `custom_components/rfplayer/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "RfPlayer"

## Configuration

This integration supports configuration flow to

- select the RfPlayer USB device
- configure RfPlayer options (receiver modes, init script...)
- configure RF device options
- add RF devices manually

### Gateway configuration

For best performance, it's recommended to limit the number of enabled receiver protocols. By default all protocols are enabled.

For additional RfPlayer tuning, it's possible to execute a set of RfPlayer commands when the integration is loaded. The configuration is a list of comma-separated low-level commands. For example, it's possible to fine-tune the sensivity or selectivity of the receiver.

### Manual RF device configuration

By default, RF device are added automatically to HomeAssitant upon receipt of RfPlayer packet matching a known device that has not been already configured. The RF device will be created with the first matching RF device profiles. The automatic creation option can be disabled afterward if you don't want to add new devices anymore.

Automatic device creation is mostly useful for sensors because most actuators are only receivers and cannot send events. In that case, the RF device must be declared manually from the RfPlayer configuration menu.

Some generic RF devices can match several device profiles (e.g. Blyss devices). If you want to assign a more specific profile, you need to disable automatic device creation, delete the device that was automatically created and re-create it manually with the profile of your choice.

### Device replacement

Some RF devices like Oregon sensors will renew their addresses after changing the battery. This integration provides a RF device option named _redirect address_ to redirect events with a new address to the device entities created with the initial address. This is useful to keep the current user configuration of the device (area, labels...) while still being able to receive events with the new device address.

### Simulation

It is possible to emulate a RfPlayer to try the integration without real hardware. When the RfPlayer integration is added, simply select the simulator device instead of a real USB device.

You can use the simulate event service to try out different JSON events as if they were received on the USB serial line. Read the RfPlayer API documentation for details about the JSON payload format.

## Device profiles

A devic profile defines the mapping between RfPlayer JSON events / commands and Home Assistant platforms attributes / services.
The mapping is described in a YAML file. You can find the latest version of the [device profiles here](https://github.com/gce-electronics/HA_RFPlayer/blob/main/custom_components/rfplayer/device-profiles.yaml).
Platform attributes are extracted from the JSON payload using [JSON path](https://en.wikipedia.org/wiki/JSONPath) expressions.

List of device profiles verification with real devices:

| Profile                                     | Event verified | Command verified | Comment                    |
| ------------------------------------------- | -------------- | ---------------- | -------------------------- |
| X10 DOMIA Switch                            | ❌             | ❌               |
| Jamming Detector                            | ❌             | ❌               |
| X10 CHACON KD101 BLYSS FS20 Switch          | ❌             | ❌               |
| X10 CHACON KD101 BLYSS FS20 Lighting        | ❌             | ❌               |
| X10 CHACON KD101 BLYSS FS20 On/Off          | ✅             | ❌               |
| X10 CHACON KD101 BLYSS FS20 Motion detector | ❌             | ❌               |
| X10 CHACON KD101 BLYSS FS20 Smoke detector  | ❌             | ❌               |
| Visionic Sensor/Detector                    | ❌             | ❌               |
| Visionic Remote                             | ❌             | ❌               |
| RTS Shutter                                 | ✅             | ❌               |
| RTS Portal                                  | ❌             | ❌               |
| Oregon Temperature Sensor                   | ✅             |                  |
| Oregon Temperature/Humidity Sensor          | ✅             |                  |
| Oregon Pressure Sensor                      | ❌             | ❌               |
| Oregon Wind Sensor                          | ❌             | ❌               |
| Oregon UV Sensor                            | ❌             | ❌               |
| OWL Power Meter                             | ❌             | ❌               |
| Oregon Rain Sensor                          | ❌             | ❌               |
| X2D Thermostat Elec                         | ✅             | ✅               |
| X2D Thermostat Gas                          | ❌             | ❌               |
| X2D Detector/Sensor                         | ❌             | ❌               |
| X2D Shutter                                 | ❌             | ❌               |
| Edisio Temperature Sensor                   | ✅             |                  | No humidity sensor support |

## Future improvements

- Add user-defined device profiles
- Move device configuration (area,...) to new device instead of redirecting events
- Add more platforms siren, events...

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

---

[rfplayer]: https://github.com/gce-electronics/HA_RFPlayer
[commits-shield]: https://img.shields.io/github/commit-activity/y/gce-electronics/HA_RFPlayer
[commits]: https://github.com/gce-electronics/HA_RFPlayer/commits/main
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg
[forum]: https://forum.hacf.fr/
[license-shield]: https://img.shields.io/github/license/gce-electronics/HA_RFPlayer
[releases-shield]: https://img.shields.io/github/release/gce-electronics/HA_RFPlayer
[releases]: https://github.com/gce-electronics/HA_RFPlayer/releases
