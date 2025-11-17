#!/usr/bin/env python3
"""
Data Validator Script

This script validates data against rules defined in an Excel file.
It supports different scopes (all, each: column, when: condition) and 
different validation rules (must have, allow, no).

Version: 1.0.0
Last Updated: 2024-11/14

Updates:
- 2025-11-14 (v1.0.0): Initial release with Cerberus integration for validation.
- 2025-11-17 (v1.0.1): Added API function to allow programmatic use.

Author: izzy.yang@wppunite.com
"""

import argparse
import logging
import sys
import os
import glob
from typing import Dict, List, Any, Set, Optional
import pandas as pd
from datetime import datetime
from cerberus import Validator
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------

def setup_logger(log_file: str) -> logging.Logger:
    """Set up logger to write to both file and console."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Clear handlers if re-run in same process
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(fmt)
    # ch.setFormatter(fmt) # Uncomment this line to add timestamps to console logs

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


# ---------------------------------------------------------------------
# Data I/O Functions
# ---------------------------------------------------------------------

def get_project_root() -> Path:
    if getattr(sys, 'frozen', False):  
        # Running as PyInstaller EXE - use directory where EXE is located
        return Path(sys.executable).parent
    else:
        # Running from source
        return Path(__file__).resolve().parents[1]


def get_latest_data_cache() -> Optional[str]:
    """Find the most recent data cache parquet file."""
    script_dir = get_project_root()
    cache_pattern = str(script_dir / "data/data cached *.parquet")
    cache_files = glob.glob(cache_pattern)
    
    if not cache_files:
        return None
    
    # Sort by modification time and return the most recent
    cache_files.sort(key=os.path.getmtime, reverse=True)
    return cache_files[0]


def save_data_cache(df: pd.DataFrame, logger: logging.Logger) -> None:
    """Save dataframe to parquet cache file with timestamp."""
    script_dir = get_project_root()
    
    # Remove existing cache files before creating new one
    cache_pattern = str(script_dir / "data/data cached *.parquet")
    existing_cache_files = glob.glob(cache_pattern)
    
    if existing_cache_files:
        for cache_file in existing_cache_files:
            try:
                os.remove(cache_file)
                logger.info(f"\n🗑️ Removed old cache file: {os.path.basename(cache_file)}")
            except Exception as e:
                logger.error(f"\n🐞 Failed to remove old cache file {os.path.basename(cache_file)}: {e}")
    else:
        logger.info("🗑️ No existing cache files to remove.")
    
    # Create new cache file
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cache_filename = f"data cached {timestamp}.parquet"
    cache_path = os.path.join(script_dir, cache_filename)
    
    try:
        df.to_parquet(cache_path, index=False)
        logger.info(f"\n📦 Data cached successfully: {cache_filename}")
    except Exception as e:
        logger.error(f"\n🐞 Failed to save data cache: {e}")
        
        
def load_data(file_path: str, sheet_name: str, logger: logging.Logger) -> pd.DataFrame:
    """Load data from Excel file or cache."""
    # Option 1: Load from cache parquet file
    if file_path == "use_cache":
        cache_file = get_latest_data_cache()
        
        # Error handling: no cache file found
        if cache_file is None:
            logger.error("🐞 No cache file found. Please run with actual data file first to create cache.")
            sys.exit(1)
        
        # Load from cache parquet file
        try:
            file_size = os.path.getsize(cache_file) / (1024 * 1024)  # Convert to MB
            logger.info(f"\n📊 Loading data from cache: {os.path.basename(cache_file)}, Size: {file_size:.2f} MB")
            df = pd.read_parquet(cache_file)
            logger.info(textwrap.dedent(f"""
                📊 Data Load Summary (from Cache)
                - File: {os.path.basename(cache_file)}
                - Shape: {df.shape}
                - Columns: {', '.join([f'{col} ({df[col].dtype})' for col in df.columns])}"""))
            
            return df
        
        except Exception as e:
            logger.error(f"🐞 Failed to load cache file {cache_file}: {e}")
            sys.exit(1)
    
    # Option 2: Load from Excel file
    else:
        # Load from Excel file
        try:
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
            logger.info(f"\n📊 Loading data from Excel: {file_path}, Sheet: {sheet_name}, Size: {file_size:.2f} MB")
            df = pd.read_excel(file_path, sheet_name=sheet_name, keep_default_na=False, na_values=[""])
            logger.info(textwrap.dedent(f"""
                📊 Data Load Summary (from Original File)
                - File: {file_path}
                - Sheet: {sheet_name}
                - Shape: {df.shape}
                - Columns: {', '.join([f'{col} ({df[col].dtype})' for col in df.columns])}"""))
            # Save to parquet cache (every time we load from Excel)
            save_data_cache(df, logger)
            
            return df
        
        except Exception as e:
            logger.error(f"🐞 Failed to load data from {file_path}: {e}")
            sys.exit(1)


def load_rules(file_path: str, sheet_name: str, logger: logging.Logger) -> pd.DataFrame:
    """Load validation rules from Excel file."""
    try:
        logger.info(f"\n🚦 Loading rules from Excel: {file_path}, Sheet: {sheet_name}")
        df = pd.read_excel(file_path, sheet_name=sheet_name, keep_default_na=False) # Empty cells will be parsed as '' instead of NaN
        logger.info(textwrap.dedent(f"""
            🚦 Rule Load Summary
            - File: {file_path}
            - Sheet: {sheet_name}
            - Shape: {df.shape}
            - Columns: {', '.join([f'{col} ({df[col].dtype})' for col in df.columns])}"""))
        
        return df
    
    except Exception as e:
        logger.error(f"🐞 Failed to load rules from {file_path}: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------
# Preprocessing Data
# ---------------------------------------------------------------------

def preprocess_data(data: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    """preprocess data before validation."""
    data_processed = data.copy()

    # # Convert NaN values in non-numeric or datetime columns to empty strings
    # for column in data_processed.columns:
    #     if not pd.api.types.is_numeric_dtype(data_processed[column]) or pd.api.types.is_datetime64_any_dtype(data_processed[column]):
    #         data_processed[column] = data_processed[column].fillna('')
    #         logger.debug(f"Converted NaN values to empty strings in non-numeric column '{column}'")

    logger.info("\n🏗️ Data preprocessing completed: (placeholder, currently nothing is changed)")
    return data_processed


# ---------------------------------------------------------------------
# Parsing conditions and validation
# ---------------------------------------------------------------------

def parse_value(value_raw: Any, logger: logging.Logger) -> Any:
    """Parse comma-separated values, handling special cases."""
    # Handle empty or NaN values
    if pd.isna(value_raw) or str(value_raw).strip() == '':
        return None
    
    # Handle special values - Boolean
    if value_raw == 1 or value_raw == '1':
        return True
    
    # Handle special values - Date range
    if value_raw.startswith("all dates in range: "):
        range_part = value_raw.replace("all dates in range: ", "").strip()
        
        try:
            # Extract start and end dates
            start_str, end_str = range_part.split(' - ')
            start_date = pd.to_datetime(start_str.strip())
            end_date = pd.to_datetime(end_str.strip())
            
            # Generate all dates in the range
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')            
            
            # Convert to string format to match how data is stored
            vals = [pd.Timestamp(date) for date in date_range]
            logger.debug(f"Parsed date range '{value_raw}' into {len(vals)} dates from {start_date.date()} to {end_date.date()}")   
            return vals
        except Exception as e:
            logger.error(f"🐞 Failed to parse date range '{value_raw}': {e}")
            sys.exit(1)
    
    # Handle list format (normal case)
    try:
        vals = eval(value_raw)
        return vals      
    except Exception as e:
        logger.error(f"🐞 Failed to parse values from '{value_raw}': {e}")
        sys.exit(1)


def parse_rules_to_validation_schema(rule: pd.Series, logger: logging.Logger) -> Dict[str, Any]:
    """Convert validation rule to Cerberus schema format."""
    logger.info(f"\n📝 Parsing rule with column being '{rule['column']}', scope being '{rule['scope']}'")
    try:
        column = rule['column']
        allowed = parse_value(rule['allowed'], logger)
        contains = parse_value(rule['contains'], logger)
        not_empty = parse_value(rule['not_empty'], logger) 
        
        # Create Cerberus schema for this column. c.f. https://docs.python-cerberus.org/schemas.html
        schema = {column: {}}
        
        # Add validation rules based on the new column format
        if contains:
            schema[column]['contains'] = contains
        if allowed:
            schema[column]['allowed'] = allowed
        if not_empty:
            schema[column]['empty'] = False
        
        logger.debug(f"Created validation schema: {schema}")
        return schema
        
    except KeyError as e:
        logger.error(f"🐞 Missing required column in rule: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"🐞 Failed to parse rule to validation schema: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------

def validate_data_single_rule(data_dict: Dict[str, Any], rule_dict: Dict[str, Any], logger: logging.Logger) -> None:
    """Validate one column (pd.Series) using Cerberus schema coming from one row in the rule file."""
    # Validate using Cerberus
    validator = Validator(rule_dict)
    is_valid = validator.validate(data_dict)

    if is_valid:
        logger.info("✅ PASS - All validations passed")
        return True
    else:
        logger.error("❌ FAIL - These errors are found:")
        for field, errors in validator.errors.items():
            for error in errors:
                logger.error(f"  - {field}: {error}")
        return False


def validate_data(data: pd.DataFrame, rule: pd.DataFrame, logger: logging.Logger) -> bool:
    """Validate all data against all rules."""
    passed_count = 0
    failed_count = 0
    
    logger.info(f"\n🔽 Validating data against {len(rule)} rules... 🔽")
    
    # Check each rule (i.e. a row in the rule Excel file)
    for idx, single_rule in rule.iterrows():

        column = single_rule["column"].strip()
        scope = single_rule["scope"].strip()
        
        # parse rules to validation schema (dictionary)
        rule_dict = parse_rules_to_validation_schema(single_rule, logger)
        
        # Create a copy of data with NaN values replaced by empty strings to match what users expect & provide
        # Use the original data for datetime/numeric based calculations; the cleaned version is passed into validation
        data_cleaned = data.copy() 
        data_cleaned = data_cleaned.fillna('') 
        
        # No scope -> validate entire column
        if scope == '':

            logger.info(f"\n📏 Validating Column '{column}' on full dataset")
            data_dict = {column: data_cleaned[column].unique()}
            result = validate_data_single_rule(data_dict, rule_dict, logger)
            
        # Special scope options "each month/date of: <date_column>"
        elif scope.startswith("each"):
            
            # Check if date_column exists and is datetime type
            date_column = scope.split(":", 1)[-1].strip()
            if date_column not in data.columns:
                logger.error(f"🐞 Date column '{date_column}' not found in data")
                all_passed = False
                continue
            if not pd.api.types.is_datetime64_any_dtype(data[date_column]):
                logger.error(f"🐞 Column '{date_column}' is not a datetime column, found type: {data[date_column].dtype}")
                all_passed = False
                continue
            
            # Monitor validation status for all months/dates
            result = True
            
            # Validate for each date
            if scope.startswith("each date of"):
                
                date_values = data[date_column].dt.date.unique()
                for date_value in date_values:
                    logger.info(f"\n📏 Validating Column '{column}' where `{str(date_column)}` == '{str(date_value)}'")
                    data_dict = {column: data_cleaned[data[date_column].dt.date == date_value][column].unique()} # Use original data as mask, cleaned data for validation
                    result = validate_data_single_rule(data_dict, rule_dict, logger)
                    if not result:
                        result = False
            
            # Validate for each month           
            elif scope.startswith("each month of"):
                
                month_values = data[date_column].dt.to_period('M').unique()
                for month_value in month_values:
                    logger.info(f"\n📏 Validating Column '{column}' where `{str(date_column)}` == '{str(month_value)}'")
                    data_dict = {column: data_cleaned[data[date_column].dt.to_period('M') == month_value][column].unique()} # Use original data as mask, cleaned data for validation
                    result = validate_data_single_rule(data_dict, rule_dict, logger)
                    if not result:
                        result = False
                        
            else:
                logger.error(f"🐞 Unknown 'each' scope format: '{scope}', currrently only supports 'each date of: <date_column>' and 'each month of: <date_column>'")
                result = False
        
        # Regular condition scope     
        else:
            # Validate rows matching the condition
            try:
                logger.info(f"\n📏 Validating Column '{column}' where '{scope}'")
                data_dict = {column: data_cleaned.query(scope)[column].unique()}
                if not data_dict[column].size:
                    logger.warning(f"⚠️ No rows match the condition '{scope}'. Skipping this rule.")
                    continue
                
                result = validate_data_single_rule(data_dict, rule_dict, logger)
                
            except Exception as e:
                logger.error(f"🐞 Failed to evaluate condition '{scope}': {e}")
                result = False

        # Count results
        if result:
            passed_count += 1
        else:
            failed_count += 1
    
    # Summary
    logger.info(textwrap.dedent(f"""
        =======================================
        === 🚀 Starting Data Validation 🚀 ===
        =======================================
        Total rules processed: {passed_count + failed_count}
        ✅ Passed: {passed_count}
        ❌ Failed: {failed_count}
        """))


# ---------------------------------------------------------------------
# Package interface
# ---------------------------------------------------------------------

def run_validation(data_file: str = 'use_cache',
                   data_sheet: str = '',
                   rules_file: str = 'data/data_validation_rules.xlsx',
                   rules_sheet: str = 'rules',
                   log_file: str = 'log/data_validation_report.log') -> None:
    """
    Run data validation programmatically.

    Args:
        data_file: Path to the data file. Provide the actual directory, or ingore to use the latest cached data.
        data_sheet: Sheet name in the data file. Provide the actual sheet name in excel, or ignore if using cached file.
        rules_file: Path to the rules file. Ignore to use default 'data/data_validation_rules.xlsx' in the project root.
        rules_sheet: Sheet name in the rules file. Ingore to use default 'rules' sheet.
        log_file: Path to the log file. If left blank. Ingore to use default 'log/data_validation_report.log' in the project root.
    """
    os.makedirs(os.path.dirname(rules_file), exist_ok=True)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger = setup_logger(log_file)

    logger.info(textwrap.dedent("""
        =======================================
        === 🚀 Starting Data Validation 🚀 ===
        =======================================
    """))

    # Load data
    data_df = load_data(data_file, data_sheet, logger)

    # Load rules
    rules_df = load_rules(rules_file, rules_sheet, logger)

    # Preprocess data
    data_df_processed = preprocess_data(data_df, logger)

    # Run validation
    all_passed = validate_data(data_df_processed, rules_df, logger)

    input("\nPress Enter to exit...")
    sys.exit(0)

# ---------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate data against rules defined in Excel file."
    )
    
    def clean_path_input(user_input: str) -> str:
        """Clean and normalize path input from user."""
        if not user_input:
            return ""
        
        # Strip whitespace
        cleaned = user_input.strip()
        
        # Remove surrounding quotes (both single and double)
        if (cleaned.startswith('"') and cleaned.endswith('"')) or \
           (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1]
        
        # Normalize path separators to OS-appropriate format
        cleaned = os.path.normpath(cleaned)
        
        return cleaned
    
    # Prompt for data file if not provided
    data_file = clean_path_input(input("Enter data file path (or press Enter to use cached data): "))
    if data_file:
        data_sheet = input("Enter data sheet name: ").strip()
        data_args = [data_file, data_sheet]
    else:
        data_args = ['use_cache', '']
    
    # Prompt for rules file
    default_rules_path = get_project_root() / "data/data_validation_rules.xlsx"
    rules_file = clean_path_input(input(f"Enter rules file path (or press Enter for default '{default_rules_path}'): "))
    if not rules_file:
        rules_file = default_rules_path
        os.makedirs(os.path.dirname(rules_file), exist_ok=True)
    
    rules_sheet = input("Enter rules sheet name (or press Enter for default 'rules'): ").strip()
    if not rules_sheet:
        rules_sheet = "rules"
    
    # Prompt for log file
    default_log_path = get_project_root() / "log/data_validation_report.log"
    log_file = clean_path_input(input(f"Enter log file path (or press Enter for default '{default_log_path}'): "))
    if not log_file:
        log_file = default_log_path
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Create namespace object with the collected inputs
    args = argparse.Namespace()
    args.data = data_args
    args.rule = [rules_file, rules_sheet]
    args.log = log_file
    
    return args

def main():
    """Main execution function."""
    args = parse_args()
    logger = setup_logger(args.log)

    logger.info(textwrap.dedent(f"""
        =======================================
        === 🚀 Starting Data Validation 🚀 ===
        =======================================
        """))
    
    # Load data
    data_df = load_data(args.data[0], args.data[1], logger)
    
    # Load rules
    rules_df = load_rules(args.rule[0], args.rule[1], logger)

    # Preprocess data
    data_df_processed = preprocess_data(data_df, logger)

    # Run validation
    validate_data(data_df_processed, rules_df, logger)
    
    input("\nPress Enter to exit...")
    sys.exit(0)


if __name__ == "__main__":
    main()