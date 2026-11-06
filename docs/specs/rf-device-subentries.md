# RF device subentries

**Status:** Proposed
**Context:** RFPlayer modernization branch and GitHub issue [#101](https://github.com/gce-electronics/HA_RFPlayer/issues/101)

## Summary

Represent each configured RF device as a Home Assistant config subentry owned by its RFPlayer gateway config entry. Multiple gateways with distinct reported MAC addresses are supported. Keep each gateway's connection details and gateway-wide options on its own parent entry. This makes device management visible through Home Assistant's integration UI while allowing users to add another gateway from the global Devices page.

The implementation should use Home Assistant's native config subentry API. [Home Assistant added subentries in 2025.7](https://www.home-assistant.io/blog/2025/07/02/release-20257/); its [integration guidance](https://developers.home-assistant.io/docs/core/integration/config_flow/#subentry-flows) describes user and reconfigure flows. The repository's current `hacs.json` declares Home Assistant 2026.2.0, which is new enough; the supplied `AGENTS.md` says 2025.1.0 and should be reconciled with that metadata before implementation.

## Goals

- Let users add RF devices from the existing RFPlayer integration's subentry UI, without attempting to create a second gateway entry.
- Give every RF device its own editable and removable configuration record.
- Preserve automatic event-based device discovery, manual configuration, pairing, and address replacement.
- Migrate existing device configuration without losing device identity, entity IDs, history, areas, or other registry customizations.
- Keep gateway connection setup independent from RF device configuration.
- Allow integration setup and migration when the gateway-reported MAC cannot be read.

## Non-goals

- Support multiple RFPlayer gateways in one Home Assistant instance, identified by their reported MAC addresses.
- Add a custom Home Assistant frontend component or modify Home Assistant's fixed list of integrations that support the global Devices-page pairing button.
- Change RF protocol profiles or add support for new RF protocols.
- Make the RFPlayer-reported MAC an immutable hardware serial number.

## Configuration model

### Parent config entry

Each parent entry represents one RFPlayer gateway. Multiple parent entries may be configured when they report distinct MAC addresses.

- `entry.data`: gateway connection details, including the serial path, simulator, or TCP proxy address.
- `entry.options`: gateway-wide settings such as automatic addition, reconnect interval, receiver protocols, init commands, and verbose logging.

### RF device subentry

Use one subentry type, `rf_device`. A subentry stores the fields currently represented by `RfPlayerDeviceInfo`:

- protocol and address (required)
- device model (optional)
- selected profile (required)
- redirected address (optional)
- event data used by the current profile/entity setup path (optional)

Use the device's canonical RF ID, derived from protocol and address, as the subentry unique ID. The subentry title should be a readable protocol/model/address label. The canonical ID and existing device registry identifiers must remain stable across migration and address replacement.

The built-in jamming device is currently supplied by `DEFAULT_DEVICES` rather than being a user-configured device. Preserve its current behavior without requiring users to create a subentry for it.

## User flows

### Add a device

The subentry's `user` flow should offer:

1. **Configure manually:** select protocol, address, and a compatible device profile. Offer the existing pairing command where supported. Send the pairing command before persisting the subentry; if pairing fails, show an error and do not add the device.
2. **Listen for a device:** capture supported, unknown RF events and let the user select a detected device and profile. This is an explicit user flow; Home Assistant subentry flows do not have a separate discovery source/step.

Subentry creation must reject duplicate canonical RF IDs and unsupported protocol/profile combinations.

### Discovery window

- Capture for up to **10 minutes** per discovery session. Do not add a duration selector or a persistent gateway setting for this one-off flow.
- While listening, keep a native config-flow menu step available with a **Finish listening** action. Selecting it ends capture immediately and proceeds to the captured-device results. Do not require users to wait for the full window.
- Stop capture automatically at the 10-minute deadline. When the flow next advances, show the captured-device results; do not require a live-updating timer or results list in the config-flow UI.
- Finishing early or reaching the deadline should return all captured supported devices.
- Events from already configured devices must continue through normal event handling and must not be swallowed by the discovery listener.
- Keep the latest event per canonical ID during one discovery session. Ignore unsupported profiles and report a useful no-devices result if none remain.
- Ensure the flow text and capture deadline agree. The current branch uses 500 seconds while its translation says 60 seconds; resolve that mismatch as part of this work.

### Reconfigure and remove

- Implement a subentry `reconfigure` flow for device settings, including redirected address.
- Replacing a device means updating the existing subentry's redirect address, not creating a second configured device. Require compatible protocol and profile and reject a redirect address already assigned to another device.
- Removing a subentry removes that RF device from integration configuration and runtime processing. It must not remove unrelated devices or the parent gateway entry.
- Verify Home Assistant registry behavior so users retain device area, labels, entity IDs, and history when a device is replaced. Explicit removal should have a documented and tested entity/device registry outcome.

### Automatic addition

When automatic addition is enabled and an event belongs to a supported, unknown RF device, create a subentry using the existing profile matching behavior. Do not add unknown or unsupported frames. After creation, update runtime state so subsequent events are delivered to the new device without duplicate entities or duplicate subentries.

Runtime-created subentries must be reflected in the UI. Confirm whether subentry changes reload the parent entry in the supported Home Assistant versions; avoid unnecessary gateway disconnect/reconnect cycles if the runtime can apply the change directly.

## Migration

Migrate device records currently stored in the parent entry's data/options into `rf_device` subentries. Preserve the parent connection details and gateway-wide options, and remove the device map from parent options after successful migration.

Migration requirements:

- Preserve protocol, address, model, profile, redirect address, and event data for each configured device.
- Assign each migrated subentry the original canonical RF ID as its unique ID.
- Be idempotent and avoid creating duplicate subentries if migration is retried.
- Preserve entity registry unique IDs and device identifiers so entity IDs, history, areas, labels, and user customizations remain associated with the same RF device.
- Handle both released legacy entries and entries produced by the current branch's interim version 2.0 storage layout, if that layout has been used by testers.
- Keep the built-in jamming default behavior without turning it into a duplicate user-managed subentry.
- Do not make migration fail just because the RFPlayer cannot currently be probed for a gateway ID.

Before implementation, choose the final config-entry version. If the branch's version 2.0 format has not shipped, migrate legacy entries directly to the final subentry format. If users may already have version 2.0 entries, add an explicit 2.0-to-final migration as well.

## Gateway identity and probe

The gateway probe reads the MAC value returned by `STATUS SYSTEM JSON` and uses it as the config-entry unique ID. Two connections reporting the same MAC identify the same gateway, so Home Assistant must reject a second entry with that MAC. `SETMAC` can change the reported value; users must keep MAC values unique across gateways. A collision caused by assigning the same value with `SETMAC` is unsupported and must not be treated as two independent gateways. The [RFPlayer user guide](https://community.jeedom.com/uploads/short-url/gCx2nall7A7PN3qfpwCUfsPKzoV.pdf) documents `SETMAC` commands.

- New setup must remain possible when the probe times out, returns malformed data, or has no MAC field. Set the config-entry unique ID only when a valid value is available.
- Migration must preserve and load the existing entry if the gateway is unavailable; it must not store a `None` value as though a valid unique ID had been acquired.
- Normalize the returned value consistently (including optional `0x` prefixes and casing) and validate its shape before using it.
- Do not use the gateway MAC as an RF device subentry ID. Child IDs come from the RF protocol/address canonical ID.
- Allow multiple config entries for distinct gateways while relying on Home Assistant's unique-ID check to reject a repeated MAC.

## Compatibility and documentation

- Confirm `hacs.json` is the source of truth for the minimum Home Assistant version. Its current minimum, 2026.2.0, satisfies the 2025.7 subentry requirement; update stale developer instructions that claim 2025.1.0 if that is no longer supported.
- Document the per-device subentry add, edit, remove, discovery, and replacement flows in the README.
- Update translations for subentry flow titles, descriptions, errors, and abort reasons.
- Preserve the existing TCP proxy, simulator, manual add, and pairing behavior unless a specific compatibility change is approved.

## Acceptance criteria

- The integration exposes a native **Add RF device** subentry action for each gateway. Starting a gateway config flow remains available while other gateways are configured.
- Users can manually add an RF device with a compatible profile and optionally pair it when the protocol supports transmission.
- Users can discover supported transmitting devices within the selected capture window and add one as a subentry.
- Automatic addition creates at most one subentry for a supported canonical RF ID and makes it active for subsequent events.
- Users can reconfigure a device's redirect address and remove one device without affecting other devices or the gateway.
- Replacing an RF device preserves the existing device/entity identity and registry customizations.
- Existing gateway and RF device settings migrate to their new locations without data loss or duplicate subentries.
- Setup and migration succeed when a gateway MAC probe is unavailable; a valid reported ID is normalized and used when present.
- Discovery captures for at most 10 minutes, can be finished early through the config-flow menu, and returns captured devices after early finish or deadline expiration.
- Tests cover migration from each supported storage layout, duplicate IDs, probe failure/malformed response, subentry add/reconfigure/remove, automatic addition, replacement, and discovery timeout/early finish.

## Findings and design decisions recorded

- Issue #101 asks for adding an RF device from the existing integration UI rather than the global Devices-page flow that attempts to add a second integration instance.
- Aohzan's proposal maps one gateway to the parent config entry and each RF device to a config subentry. This is a better fit than extending only the current options menu and follows Home Assistant's intended use for repeatable child configuration.
- The modernization branch already introduces gateway/device data separation, session lifecycle extraction, pairing, discovery, and replacement. Those changes are useful groundwork, but device records should end in subentries rather than remain in the parent options dictionary.
- The current branch's discovery duration (500 seconds) conflicts with its UI text (60 seconds); the proposed product default is 120 seconds with optional longer per-session windows.
- The gateway MAC probe should be best-effort because the reported value is configurable and can be unavailable. It is not a reason to block adding RF devices.
- The review found no explicit feature spec in the branch before this document. The requirements above consolidate issue #101, Aohzan's subentry proposal, and the branch review findings.
