# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Validation of parameter based on the RPC Type


## [0.6.2] - 2025-02-04
### Changed
- Minimal supported version of pySHV is now 0.8.0

### Fixed
- Builtin `!set` now supports int and float options
- Exit when implementation exception is encountered instead of getting stuck


## [0.6.1] - 2024-10-31
### Added
- Configuration options `call_attempts`, `call_timeout`, and `autoget_timeout`
  to allow control over call timeouts

### Fixed
- Call timeout handling so shvcli no longer gets stuck on timeout
- Configuration option `config.cache` is no longer reported as invalid
- Output of the calls is no longer truncated (regression since 0.6.0)


## [0.6.0] - 2024-10-09
### Added
- Launch parameter `-s` to automatically subscribe right after login
- `!sub` and `!usub` now accepts multiple RIs

### Changed
- Minimal supported version of pySHV is now 0.7.1
- Received signals are now formatted and not printed on the single line
- `!subs` now prints RIs as a formatted text
- Formatted `dir` output now also provide list of signals

### Fixed
- `!sub` now correctly uses the current relative path to create RI


## [0.5.0] - 2024-08-22
### Changed
- Minimal supported version of pySHV is now 0.7.0


## [0.4.0] - 2024-04-06
### Changed
- Minimal supported version of pySHV is now 0.6.0


## [0.3.0] - 2023-01-29
### Added
- Ability to scan tree right after connection
- Automatic calling of getters when listing nodes and methods

### Changed
- Take default URL from configuration (the first host) instead of always
  connecting to the localhost
- Method results in CPON are now printed with JSON syntax highlight (There is no
  syntax lexer for CPON at the moment)

### Fixed
- `!set` now sets boolean options instead of toggling it
- `!help` now handles multiline descriptions in a better way
- `dir` and `ls` listings are now better wrapped to multiple lines


## [0.2.1] - 2024-01-18
### Fixed
- Version reported by setuptools and thus on pypi.org and readme format


## [0.2.0] - 2024-01-18
### Added
- Added builtin method `!scan` that allows discovery of SHV tree
- Validation of CPON when entering it on CLI
- Ability to set some configuration options from configuration file
- Added option to switch to Vi like input mode (`vimode` config option)
- Keep cache between process invocations

### Changed
- Builtin commands `raw`, `autoprobe` and `debug` were replaced with `set`
- Long CPON is now printed on multiple lines instead of one long

### Fixed
- Bultin functions `!subscribe`, `!usubscribe` and `!tree` now correctly uses
  full SHV path and not just path from argument


## [0.1.1] - 2023-11-22
### Changed
- Interrupt (Ctrl-C) now terminates prompt input and method call in primary loop
  instead of terminating it

### Fixed
- Switch to `/` is not posible because this path was considered invalid
- Fixed color scheme with white terminals
- Fixed hang when switching to invalid path


## [0.1.0] - 2023-11-10
### Added
- Initial implementation
