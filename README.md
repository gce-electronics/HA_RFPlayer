# HA_RFPlayer

RFPlayer custom component for Home assistant

_/!\ ALPHA VERSION /!\\_
Not really tested.

## Installation

Copy the `custom_component/rfplayer` folder in your config directory.

Go to Home-Assistant UI, Configuration > Integrations, button (+ Add Integration) and search GCE RFPlayer

Select the USB device in the list and valid.

## Usage

Sensor are created automatically

You can use the service `rfplayer.send_command` to send commands to your devices.

## Credits

Based on rflink integration.
