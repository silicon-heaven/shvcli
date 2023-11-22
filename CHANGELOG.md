# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
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
