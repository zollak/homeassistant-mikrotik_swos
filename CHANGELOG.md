# Changelog

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
