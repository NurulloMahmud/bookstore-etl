from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# conversion rate
EUR_TO_USD = 1.2

# data folders to process
DATA_FOLDERS = ["DATA1", "DATA2", "DATA3"]

# output paths
OUTPUT_DIR = 'output'
CHARTS_DIR = 'output/charts'
RESULTS_DIR = 'output/results'
DASHBOARD_DIR = 'dashboard'

NULL_VALUES = ['NULL', 'None', '', ' ', '\t', None]

DATE_FORMAT = '%Y-%m-%d'