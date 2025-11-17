# Changelog

All notable changes to the Data Validation QA Script will be documented in this file.

## [1.0.0] - 2024-11-14

### Added
- Initial release of data validation script
- Excel-based validation rules support
- Cerberus integration for validation logic
- Automatic parquet data caching
- Interactive command-line interface
- Support for multiple validation scopes (full dataset, date-based, conditional)
- Comprehensive logging with file and console output
- PyInstaller EXE compilation support
- Date range validation with "all dates in range" syntax
- Validation rule types: allowed values, contains, not_empty

### Features
- Validates data against Excel-defined rules
- Caches large datasets as parquet files for performance
- Supports "each date of" and "each month of" scoping
- Automatic cleanup of old cache files
- Portable EXE deployment with relative path resolution (file not generated yet)

## [1.0.1] - 2025-11-17

### Added
- API function and pyproject.toml to allow being installed and called as package
- Updated 