# Data Validation QA Script

A data validation tool that validates data against configurable rules in Excel files.

## Overview

This script validates data from Excel files against a set of predefined rules to ensure data quality and consistency. It supports various validation scopes including full dataset validation, date-based partitioning, and conditional validation. 

Core validation logics are from the Cerberus validation library.

## Preparation

### Installation & Setup

1. Python version >= 3.11 is needed
2. In the command line interface, go to a desirable folder and run: `pip install --upgrade git+https://github.com/IzzyT-Yang/izzys-data-validator.git`

### Source Files Perparation

1. Ensure you have a `data_validation_rules.xlsx` in the data folder (so you can use the default settings), or in another directory and manually input the file directory when running the script/using it in Python. A sample file is saved in `data\data_validation_rules - template.xlsx` in this project.
2. Have the raw data ready in Excel format. This can be saved anywhere.
3. Make sure both files are closed when running the script

## Use Script in Interactive Mode

After installing with pip, simply run: `run_validation`.

The script will prompt you for:
1. **Data file path** (or press Enter to use cached data)
2. **Data sheet name** (if using Excel file)
3. **Rules file path** (or press Enter for default)
4. **Rules sheet name** (or press Enter for default "rules")
5. **Log file path** (or press Enter for default)

## Use as Python Module

After installing with pip, go into Python and run `from validator import run_validation`

Then you can use `run_validation()` for the validation task. Use `help(run_validation)` to get instructions on what to put into each parameter. 

## Data Caching

The script automatically creates parquet cache files for faster subsequent runs:

- **First run**: Loads from Excel and creates cache
- **Subsequent runs**: Use cache (much faster) if no new data file paths are passed in
- **Cache management**: Old cache files are automatically cleaned up

Cache files are named: `data cached YYYY-MM-DD HH:MM:SS.parquet`

## Author

**Izzy Yang** - izzy.yang@wppunite.com

## Version History

See the full changelog here: [CHANGELOG.md](CHANGELOG.md)