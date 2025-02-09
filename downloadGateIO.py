"""
This Python script automates the process of downloading candlestick data for active trading pairs from the Gate.IO cryptocurrency exchange. It utilizes the Gate.IO API to fetch trading pairs settled in USDT and BTC and then downloads the historical candlestick data for various timeframes. The script supports multithreading to enhance the efficiency of downloads and handles data integrity checks for the downloaded gzip files.

Features:
- Fetches active USDT and BTC trading pairs using the Gate.IO API.
- Downloads candlestick data for specified timeframes (1m, 5m, 1h, 4h, 1d) over a period starting from 50 days ago.
- Supports multithreading for faster downloads of candlestick data across different timeframes and trading pairs.
- Performs data integrity checks on the downloaded gzip files, ensuring that corrupt files are identified and re-downloaded if necessary.
- Organizes downloaded data into a structured directory format based on ticker symbols and timeframes.

Usage:
- The script is designed to be executed directly, with no additional arguments required.
- Users can customize the list of base assets, timeframes, and the number of threads for downloading data.

Dependencies:
- `os` for directory operations.
- `requests` for making HTTP requests to the Gate.IO API and downloading files.
- `gzip` for handling gzip file operations.
- `datetime` for date manipulations to determine the time range for data downloads.
- `concurrent.futures` for implementing multithreading.

Note: Before running the script, ensure that the necessary Python packages are installed and that you have sufficient disk space for the downloaded data.
"""

import os
import requests
import gzip
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

#Download active trading pairs from Gate.IO
def get_usdt_btc_trading_pairs():
    # Set up the API endpoint and parameters
    endpoint = "https://api.gateio.ws/api/v4/spot/currency_pairs"
    params = {"settle": "usdt,btc,eth"}

    # Make the API request
    response = requests.get(endpoint, params=params)
    
    # Parse the response JSON and extract the trading pairs
    pairs = [pair["id"] for pair in response.json()]

    # Return the list of trading pairs
    return pairs

# Set the base URL for the Gate.io data download
base_url = "https://download.gatedata.org"

# Define the directory to save the downloaded files
# save_dir = "user_data/priceData/data/gateio"
save_dir = "data/gateio"

baseAssets = ['BTC', 'ETH' ,'USDT']
# baseAssets = ['USDT']

# Define the number of threads to use for downloading files
num_threads = 10

# Define the available timeframes
timeframes = ["1m", "5m", "1h", "4h", "1d"]
# timeframes = ["1m"]

# Define the function to download a file from the Gate.io data download URL
def download_file(url, save_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

# Define the function to download all available candlestick data for a given ticker and timeframe
def download_candlestick_data(ticker, timeframe):
    # Set the parameters for the candlestick data URL
    biz = "spot"
    today = date.today() - timedelta(days=50)
    # last_month = date.today() - timedelta(days=50)
    year_month = today.strftime("%Y%m")

    # Create a subfolder inside the save directory for the current ticker and timeframe
    ticker_dir = os.path.join(save_dir, ticker, timeframe)
    os.makedirs(ticker_dir, exist_ok=True)

    # Download candlestick data for each month, starting from last month
    while True:
        # Check if ticker ends with any value in baseAssets
        if any(ticker.endswith(asset) for asset in baseAssets):
            url = f"{base_url}/{biz}/candlesticks_{timeframe}/{year_month}/{ticker}-{year_month}.csv.gz"
            save_path = os.path.join(ticker_dir, f"{ticker}-{year_month}.csv.gz")
            if os.path.exists(save_path):
                # Check if the existing file is a valid gzip file
                try:
                    with gzip.open(save_path, 'rb') as f:
                        # Try reading some data to ensure it's a valid gzip file
                        f.read(1)
                    # print(f"File {save_path} is a valid gzip file, skipping download")
                    # File is valid, skip download
                    pass
                except (OSError, EOFError) as e:
                    # If an error occurs, the file is not a valid gzip file
                    print(f"File {save_path} is not a valid gzip file. Deleting file...")
                    os.remove(save_path)
                    # After deleting, you might want to download the file again
                    try:
                        download_file(url, save_path)
                        print(f"Redownloaded {url} to {save_path}")
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 404:
                            # print(f"{url} not found. Skipping...")
                            break
            else:
                # File does not exist, proceed with download
                try:
                    download_file(url, save_path)
                    print(f"Downloaded {url} to {save_path}")
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        # print(f"{url} not found. Skipping...")
                        break
        else:
            # print(f"Ticker {ticker} does not end with a value contained in baseAssets, skipping...")
            # Optionally, you can decide to break or continue based on your loop's logic
            pass
            # break

        # Move to the previous month
        today = today - relativedelta(months=1)
        year_month = today.strftime("%Y%m")

# Define the function to download all available candlestick data for a given ticker
def download_candlestick_data_all_timeframes(ticker):
    # Download candlestick data for each timeframe using multithreading
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(lambda tf: download_candlestick_data(ticker, tf), timeframes)

# Define the main function to download all available candlestick data for all tickers and timeframes
def main():
    # Create the directory to save the downloaded files
    os.makedirs(save_dir, exist_ok=True)

    # Retrieve all USDT and BTC trading pairs from the Gate.io API
    tickers = get_usdt_btc_trading_pairs()

    # Initialize a single progress bar for the tickers
    progress_bar = tqdm(total=len(tickers), desc='Processing Tickers', position=0)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(download_candlestick_data_all_timeframes, ticker): ticker for ticker in tickers}
        for future in futures:
            ticker = futures[future]
            try:
                # Wait for the future to complete
                result = future.result()
                # Update the progress bar after each ticker is processed
                progress_bar.update(1)
            except KeyboardInterrupt:
                print("Keyboard interrupt detected, waiting for threads to finish...")
                executor.shutdown(wait=True)
                break
    progress_bar.close()  # Ensure the progress bar is closed properly


if __name__ == "__main__":
    main()