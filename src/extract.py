"""
Extract module - Load data from CSV, Parquet, and YAML files
"""

import pandas as pd
import yaml
from pathlib import Path


# convert users dataset into df
def load_users(data_folder: str) -> pd.DataFrame:
    filepath = Path(data_folder) / 'users.csv'
    df = pd.read_csv(filepath)
    return df


# convert orders dataset into df
def load_orders(data_folder: str) -> pd.DataFrame:
    filepath = Path(data_folder) / 'orders.parquet'
    df = pd.read_parquet(filepath)
    return df


# convert books dataset into df
def load_books(data_folder: str) -> pd.DataFrame:
    filepath = Path(data_folder) / 'books.yaml'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        books_data = yaml.safe_load(f)
    
    cleaned_books = []
    for book in books_data:
        cleaned_book = {}
        for key, value in book.items():
            # remove leading colon :
            clean_key = key.lstrip(':') if isinstance(key, str) else key
            cleaned_book[clean_key] = value
        cleaned_books.append(cleaned_book)
    
    df = pd.DataFrame(cleaned_books)
    return df


# load all data -> returns tuple of dfs (users_df, orders_df, books_df)
def load_all_data(data_folder: str) -> tuple:
    users = load_users(data_folder)
    orders = load_orders(data_folder)
    books = load_books(data_folder)
    
    return users, orders, books