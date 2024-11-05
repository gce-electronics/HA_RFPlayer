# CHANGELOG

## 1.0.0

- /!\ Complete rework, you need to remove your integration configuration and add it again, you will have to add your device again

## 0.7.1

- Fix mixup between device ID and device address in english for send_command service
- Fix RfplayerDevice available getter

## 0.7.0

- Fix default conf missing error during initialization
- Lint and code improvments
- Bump pyserial-asyncio
- Add service translation
- Handle no USB device found during init
- Replace the jamming sensor by a binary_sensor and add events catching to it
- Allow to specify manual path to USB device
- Disallow multi instance of the integration
- Fix options changes not reloading integration

## 0.6.1

- Fix incapacity to create switch entity when automatic entity add is disabled at bootstrap

## 0.6.0

- Replace deprecated async_get_registry method

## 0.5.0

- Add missing async_write_ha_state for number entity
- Add X2D/STARBOX F03 (CPL) messages parsing
- Replace deprecated methods

## 0.4.1

- Replace deprecated method `async_setup_platforms`

## 0.4.0

- Fix 2022.07 error

## 0.3.0

- Handle Oregon and Edisio protocols
- Add Jamming entities

## 0.2.1

- Rename custom_component dir according to best practices

## 0.2.0

- Add switch entity
- Create switch entity with service `send_command`
- Improve config flow and add option menu
- Add translations
- Code improvments

## 0.1.0

- Initial release
