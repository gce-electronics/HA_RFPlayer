# HA_RFPlayer

RFPlayer custom component/integration for Home Assistant

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gce-electronics&repository=HA_RFPlayer&category=integration)

### Manually

Copy the `custom_components/rfplayer` folder in `config/custom_components` of your Home Assistant

## Configuration

Go to Home-Assistant UI, Configuration > Integrations, button (+ Add Integration) and search GCE RFPlayer

Select the USB device in the list and valid.

## Usage

Sensor are created automatically if you enable it during the installation or on the option button (Integration menu)

You can use the service `rfplayer.send_command` to send commands to your devices, and add the device as a new switch entity.

## Credits

Based on rflink integration.
