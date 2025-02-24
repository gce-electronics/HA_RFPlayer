## [1.2.1](https://github.com/gce-electronics/HA_RFPlayer/compare/v1.2.0...v1.2.1) (2025-02-24)


### Bug Fixes

* **deps:** update uv lockfile ([040db83](https://github.com/gce-electronics/HA_RFPlayer/commit/040db832a19defee829700c5440a96ece506a786))

# [1.2.0](https://github.com/gce-electronics/HA_RFPlayer/compare/v1.1.0...v1.2.0) (2025-01-07)


### Features

* upgrade to pydantic v2 ([#112](https://github.com/gce-electronics/HA_RFPlayer/issues/112)) ([0562a0e](https://github.com/gce-electronics/HA_RFPlayer/commit/0562a0e6114c024c5743cf4e9b0ec30abb091655))

# [1.1.0](https://github.com/gce-electronics/HA_RFPlayer/compare/v1.0.2...v1.1.0) (2025-01-03)


### Features

* add support for X10 address ([#108](https://github.com/gce-electronics/HA_RFPlayer/issues/108)) ([fc9b2d4](https://github.com/gce-electronics/HA_RFPlayer/commit/fc9b2d4fcec6143622e1fdeb0d5f792a52087c3c))

## [1.0.2](https://github.com/gce-electronics/HA_RFPlayer/compare/v1.0.1...v1.0.2) (2024-11-13)


### Bug Fixes

* resolve command concurrency and pairing issues ([#103](https://github.com/gce-electronics/HA_RFPlayer/issues/103)) ([#102](https://github.com/gce-electronics/HA_RFPlayer/issues/102)) ([0acbfec](https://github.com/gce-electronics/HA_RFPlayer/commit/0acbfecc0d515d885eab29ddded8ef6799c689a8))

## [1.0.1](https://github.com/gce-electronics/HA_RFPlayer/compare/v1.0.0...v1.0.1) (2024-11-11)


### Bug Fixes

* resolves rts device address issue ([#97](https://github.com/gce-electronics/HA_RFPlayer/issues/97)) ([f83617b](https://github.com/gce-electronics/HA_RFPlayer/commit/f83617b9853b8a5322f677cf802cc81611490495))

# 1.0.0 (2024-11-11)


### Bug Fixes

* resolve empty init commands issue ([abb8309](https://github.com/gce-electronics/HA_RFPlayer/commit/abb8309dc8995edd68da41eceddddffe3c9f7f95))


### Features

* complete rewrite of the rfplayer integration ([1502ad8](https://github.com/gce-electronics/HA_RFPlayer/commit/1502ad80621fa2bd09d53b80dd2285330412d118))
* empty string support for init commands and improved receiver mode configuration ([38003e2](https://github.com/gce-electronics/HA_RFPlayer/commit/38003e2c4efc1f9b5ce3c40e1dc558c324928e90))


### BREAKING CHANGES

* installing the new version will breaking any existing instance because the configuration is different and there is no migration support

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
