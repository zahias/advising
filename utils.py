
# utils.py
"""Utility functions for logging and data processing."""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional


def log_info(message: str) -> None:
    """Log an info message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[INFO] {timestamp} - {message}")


def log_error(message: str, exception: Optional[Exception] = None) -> None:
    """Log an error message with optional exception details."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if exception:
        print(f"[ERROR] {timestamp} - {message}: {str(exception)}")
    else:
        print(f"[ERROR] {timestamp} - {message}")


def load_progress_excel(file) -> pd.DataFrame:
    """
    Load and process progress report Excel file.
    Merges 'Required' and 'Intensive' sheets if both exist.
    """
    try:
        # Read Excel file
        xls = pd.ExcelFile(file)
        
        # Check for Required sheet
        if 'Required' in xls.sheet_names:
            required_df = pd.read_excel(file, sheet_name='Required')
        else:
            return pd.DataFrame()
        
        # Check for Intensive sheet and merge if exists
        if 'Intensive' in xls.sheet_names:
            intensive_df = pd.read_excel(file, sheet_name='Intensive')
            # Merge the two dataframes
            df = pd.concat([required_df, intensive_df], ignore_index=True)
        else:
            df = required_df
        
        return df
        
    except Exception as e:
        log_error("Failed to load progress Excel", e)
        return pd.DataFrame()
