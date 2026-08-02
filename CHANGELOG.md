# Changelog

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
