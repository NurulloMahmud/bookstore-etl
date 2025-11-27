import pandas as pd
import numpy as np
import re
from dateutil import parser as date_parser
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import EUR_TO_USD, NULL_VALUES

# normalize the prices
def parse_price(price_str: str) -> Optional[float]:
    if pd.isna(price_str) or price_str in NULL_VALUES:
        return None
    
    price_str = str(price_str).strip()
    
    # is it euro or usd 
    is_euro = bool(re.search(r'[€]|EUR', price_str, re.IGNORECASE))
    
    # remove currency symbols and text
    cleaned = re.sub(r'[€$]|EUR|USD', '', price_str, flags=re.IGNORECASE).strip()
    
    # handle special cent notation
    cent_match = re.search(r'(\d+)\s*¢\s*(\d+)', cleaned)
    if cent_match:
        dollars = cent_match.group(1)
        cents = cent_match.group(2)
        value = float(f"{dollars}.{cents}")
    else:
        # remove cent symbol and any remaining non-numeric chars except decimal point
        cleaned = re.sub(r'¢', '', cleaned)
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        
        if not cleaned or cleaned == '.':
            return None
        
        # handle multiple decimal points case (not sure if it exists in dataset)
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        
        try:
            value = float(cleaned)
        except ValueError:
            return None
    
    # convert euro to usd
    if is_euro:
        value = value * EUR_TO_USD
    
    return round(value, 2)

# normalize timestamp values to proper datetimes
def parse_timestamp(ts_str: str) -> Optional[pd.Timestamp]:
    if pd.isna(ts_str) or ts_str in NULL_VALUES:
        return None
    
    ts_str = str(ts_str).strip()
    
    # clean up common separator issues
    ts_str = re.sub(r';', ' ', ts_str)  # replace semicolons with spaces
    ts_str = re.sub(r',\s*', ' ', ts_str)  # remove commas
    
    # normalize AM/PM variations
    ts_str = re.sub(r'A\.M\.', 'AM', ts_str, flags=re.IGNORECASE)
    ts_str = re.sub(r'P\.M\.', 'PM', ts_str, flags=re.IGNORECASE)
    ts_str = re.sub(r'\s+am\b', ' AM', ts_str, flags=re.IGNORECASE)
    ts_str = re.sub(r'\s+pm\b', ' PM', ts_str, flags=re.IGNORECASE)
    
    # handle ISO format T separator
    ts_str = re.sub(r'T', ' ', ts_str)
    
    try:
        parsed = date_parser.parse(ts_str, fuzzy=True, dayfirst=False)
        return pd.Timestamp(parsed)
    except (ValueError, TypeError):
        # try with day-first interpretation
        try:
            parsed = date_parser.parse(ts_str, fuzzy=True, dayfirst=True)
            return pd.Timestamp(parsed)
        except:
            return None


# replace possible null representations with proper NaN
def clean_null_values(df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
    df = df.copy()
    columns = columns or df.columns
    
    for col in columns:
        if col in df.columns:
            df[col] = df[col].replace(NULL_VALUES, np.nan)
            # also handle string 'nan' and whitespace-only strings
            if df[col].dtype == object:
                df[col] = df[col].apply(
                    lambda x: np.nan if (isinstance(x, str) and x.strip() in ['', 'nan', 'NaN', 'NULL', 'None']) else x
                )
    
    return df

# normalize name by removing titles/suffixes and converting to lowercase
def normalize_name(name: str) -> Optional[str]:
    if pd.isna(name):
        return None
    
    name = str(name).strip().lower()
    
    # remove common titles and suffixes
    titles = [
        r'\bmr\.?\b', r'\bmrs\.?\b', r'\bms\.?\b', r'\bdr\.?\b', r'\bprof\.?\b',
        r'\brev\.?\b', r'\bfr\.?\b', r'\bmsgr\.?\b', r'\bgov\.?\b', r'\brep\.?\b',
        r'\bsen\.?\b', r'\bamb\.?\b', r'\bthe hon\.?\b', r'\besq\.?\b',
        r'\bjr\.?\b', r'\bsr\.?\b', r'\bi+\b', r'\bii+\b', r'\biii+\b', r'\biv\b', r'\bv\b',
        r'\bphd\b', r'\bmd\b', r'\bdds\b', r'\bdo\b', r'\bdvm\b', r'\bcpa\b',
        r'\blld\b', r'\bdc\b', r'\bvm\b', r'\bret\.?\b', r'\bmiss\b'
    ]
    
    for title in titles:
        name = re.sub(title, '', name, flags=re.IGNORECASE)
    
    # clean up extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name if name else None


def transform_users(users_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and transform users data.
    
    Creates normalized versions of fields for deduplication comparison.
    """
    df = users_df.copy()
    
    # clean null values
    df = clean_null_values(df, ['name', 'address', 'phone', 'email'])
    
    # normalize phone: keep only digits for comparison
    df['phone_normalized'] = df['phone'].apply(
        lambda x: re.sub(r'[^\d]', '', str(x)) if pd.notna(x) else None
    )
    
    # normalize email: lowercase
    df['email_normalized'] = df['email'].str.lower().str.strip()
    
    # normalize name: lowercase, remove titles
    df['name_normalized'] = df['name'].apply(normalize_name)
    
    # normalize address: lowercase, simplified
    df['address_normalized'] = df['address'].apply(
        lambda x: re.sub(r'\s+', ' ', str(x).lower().strip()) if pd.notna(x) else None
    )
    
    return df


def transform_orders(orders_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and transform orders data.
    
    - Parse messy prices to USD
    - Parse messy timestamps
    - Extract date (YYYY-MM-DD)
    - Calculate paid_price = quantity * unit_price
    """
    df = orders_df.copy()
    
    # clean null values
    df = clean_null_values(df, ['unit_price', 'timestamp', 'shipping'])
    
    # normalize prices
    df['unit_price_usd'] = df['unit_price'].apply(parse_price)
    
    # normalize timestamps
    df['parsed_timestamp'] = df['timestamp'].apply(parse_timestamp)
    
    # extract date (year, month, day only)
    df['date'] = df['parsed_timestamp'].apply(
        lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None
    )
    
    # calculate paid_price
    df['paid_price'] = df['quantity'] * df['unit_price_usd']
    
    # Remove rows with invalid essential data
    df = df.dropna(subset=['unit_price_usd', 'date', 'user_id', 'book_id'])
    
    return df

# create frozenset of author sets, (we use it later as a dictionary key)
def create_author_set(author_str: str) -> Optional[frozenset]:
    if pd.isna(author_str):
        return None
    
    # split by comma
    authors = [a.strip().lower() for a in str(author_str).split(',')]
    
    # remove empty strings
    authors = [a for a in authors if a]
    
    if not authors:
        return None
    
    return frozenset(authors)


# clean and transform books data
def transform_books(books_df: pd.DataFrame) -> pd.DataFrame:
    df = books_df.copy()
    
    # clean null values
    df = clean_null_values(df, ['title', 'author', 'genre', 'publisher', 'year'])
    
    # ensure id is integer
    df['id'] = pd.to_numeric(df['id'], errors='coerce').astype('Int64')
    
    # create normalized author sets for comparison
    df['author_set'] = df['author'].apply(create_author_set)
    
    return df

# wrap everything up and deliver -> tuple: (transformed_users, transformed_orders, transformed_books)
def transform_all(users_df: pd.DataFrame, orders_df: pd.DataFrame, books_df: pd.DataFrame) -> tuple:
    users = transform_users(users_df)
    orders = transform_orders(orders_df)
    books = transform_books(books_df)
    
    return users, orders, books
