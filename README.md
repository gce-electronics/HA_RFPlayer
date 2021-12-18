# HA_RFPlayer

RFPlayer custom component for Home assistant

## Installation

Copy the `custom_component/rfplayer` folder in your config directory.

Go to Home-Assistant UI, Configuration > Integrations, button (+ Add Integration) and search GCE RFPlayer

Select the USB device in the list and valid.

## Usage

Sensor are created automatically if you enable it during the installation or on the option button (Integration menu)

You can use the service `rfplayer.send_command` to send commands to your devices, and add the device as a new entity.

## Credits

Based on rflink integration.
