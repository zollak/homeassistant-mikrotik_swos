# Changelog

## [0.3.3] - 2026-11-08

### Fixed
- **Setup failed on switches without an SFP cage** (e.g. **CRS304-4XG**, SwOS 2.19) with
  `SwOS parse: unexpected ('EOF', None)`: the switch answers `/sfp.b` with HTTP 200 and an empty
  body. An empty answer now reads as no data. (issue #9)

## [0.3.2] - 2026-11-08

### Fixed
- **SwOS Lite**: the identity and the model were swapped (the device page showed the
  identity as model and the model in the Identity sensor). Unique IDs are unchanged. (issue #5)

## [0.3.1] - 2026-11-07

### Added
- **Identity, IP address and MAC address** sensors (diagnostic) on every model, and the IP as
  the device's "Visit" link to the switch web UI. (issue #5)
- The **SFP date** code in the SFP temperature sensor's attributes. (issue #5)

### Fixed
- **SwOS Lite**: the board temperature and voltage sensors are no longer created when the
  switch does not report them (e.g. FTC11XG), instead of staying "unknown". (issue #5)

## [0.3.0] - 2026-11-06

### Fixed
- **SwOS Lite switches showed no data** (e.g. **FTC11XG**, SwOS Lite 2.18): SwOS Lite answers
  every endpoint with numbered keys (`i01`, `i02`, ...) instead of the named keys of SwOS. These
  are now translated for system info, link state, SFP diagnostics and traffic counters. Each
  key was matched against the switch's web UI. Not yet supported on SwOS Lite: the per-port
  error counters and the board temperature (not mapped yet) and port control (the write format
  is not verified, so no port switches are created). (issue #5)
- **Switches not laid out like a CSS326** (e.g. **CRS309-1G-8S+**): the integration assumed 26
  ports with two SFP+ cages at ports 25-26, so an 8-cage switch got sensors for only two SFP
  slots. The port count, the SFP count and the first SFP port now come from the switch
  (`/link.b` `prt`, `sfp`, `sfpo`), with a fallback for builds that do not report them.
  Existing entities keep their IDs. (issue #4)
- **Empty password**: the password field is optional, so a switch with no password set can
  be added (and re-authenticated). (issue #4)

### Changed
- The port selection lists the switch's own ports with their SwOS names, and the saved
  selection is kept in port order. (issue #4)

## [0.2.4] - 2026-08-19

### Added
- **System voltage** sensor read from `/sys.b` `volt` (÷10 → volts) — shown by SwOS as
  "Health → Voltage". Single-unit switches (e.g. CSS106) report it here rather than via the
  per-PSU fields. (issue #3)

### Fixed
- Ports-selection step wording no longer says "create traffic/error sensors for" — that step
  is shared by the traffic/error/**port-control** groups, so the prompt is now generic. (issue #3)

## [0.2.3] - 2026-08-19

### Fixed
- Setup crash `object of type 'int' has no len()` on single-SFP / single-unit switches
  (e.g. **CSS106-1G-4P-1S**): SwOS returns per-SFP fields (and PoE) as bare scalars instead
  of lists on these models. SFP parsing now normalizes scalars to single-element lists, and
  `_safe_get` never calls `len()` on a non-list. (issue #3)

### Added
- PoE status/current/power is now read from `/link.b` when a switch has no `/poe.b` endpoint
  (single-unit PoE models like the CSS106). (issue #3)
- Port statistics now try `/!stats.b` (with `/stats.b` fallback), matching newer SwOS. (issue #3)

### Known limitations
- On single-SFP models the SFP slot is still reported at the fixed port index 25 (cosmetic;
  data is correct).

## [0.2.2] - 2026-08-02

### Changed
- Docs: HACS default-store install is now the primary method; HACS custom repository and manual (no-HACS) install kept as alternatives.
- Dropped `httpx` from `manifest.json` requirements — Home Assistant core bundles it (minimum HA `2024.1`, unchanged).

### Notes
- The integration is now available in the **HACS default store** (no custom repository needed).

## [0.2.1] - 2026-06-23

### Added
- Expose port number and SwOS name as switch attributes.

## [0.2.0] - 2026-06-23

### Added
- Port enable/disable switch platform (a switch entity per port to enable/disable it).

## [0.1.0] - 2026-05-14

### Added
- Initial release
- SFP+ diagnostics sensors (temperature, voltage, TX/RX power, bias current)
- SFP module info as entity attributes (vendor, part number, serial, type)
- Config flow with connection validation
- HTTP Digest authentication for SwOS web interface
- SwOS .swb binary format parser
- Support for CSS326-24G-2S+ (2 SFP+ slots, ports 25-26)
