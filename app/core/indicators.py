"""Birdeye API client and technical indicator calculations"""

import requests
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os
import time
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# Solana token addresses (mainnet)
TOKEN_ADDRESSES = {
    "SOL": "So11111111111111111111111111111111111111112",  # Wrapped SOL
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "JTO": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
    "SRM": "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt",
    "STEP": "StepAscQoEioFxxWGnh2sLBDFp9d8rvKz2Yp39iDpyT",
    "FIDA": "EchesyfXePKdLtoiZSL8pBe8Myagyy8ZRqsACNCFGnvp",
    "COPE": "8HGyAAB1yoM1ttS7pXjHMa3dukTFGQggnFFH3hJZgzQh",
    "SAMO": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "MNGO": "MangoCzJ36AjZyKwVj3VnYU4GTonjfVEnJmvvWaxLac",
    "ATLAS": "ATLASXmbPQxBUYbxPsV97usA3fPQYEqzQBUHgiFCUsXx"
}


class BirdeyeDataFetcher:
    """Birdeye API client for fetching crypto market data"""
    
    def __init__(self):
        self.api_key = os.getenv("BIRDEYE_API_KEY")
        if not self.api_key:
            logger.warning("BIRDEYE_API_KEY not found in environment variables")
        self.base_url = "https://public-api.birdeye.so"
        self.headers = {"X-API-KEY": self.api_key}
        
    def get_historical_hourly(self, token_address: str, hours: int = 72) -> pd.DataFrame:
        """
        Fetch last 72 hours of hourly data
        """
        if not self.api_key:
            raise ValueError("BIRDEYE_API_KEY not configured")
            
        url = f"{self.base_url}/defi/ohlcv"
        
        # Calculate time range
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(hours=hours)).timestamp())
        
        params = {
            "address": token_address,
            "type": "1H",  # 1 hour candles
            "time_from": start_time,
            "time_to": end_time
        }
        
        try:
            logger.debug(f"Fetching historical data for {token_address}")
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}: {response.text}")
                
            data = response.json()
            
            # Wait 2 seconds before next API call to avoid rate limiting
            time.sleep(2)
            
            return self.process_candles(data.get('data', {}).get('items', []))
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {token_address}: {str(e)}")
            raise
    
    def get_current_price(self, token_address: str) -> float:
        """
        Get current price in USD for a token
        """
        if not self.api_key:
            raise ValueError("BIRDEYE_API_KEY not configured")
            
        url = f"{self.base_url}/defi/price"
        
        params = {
            "address": token_address
        }
        
        try:
            logger.debug(f"Fetching current price for {token_address}")
            response = requests.get(url, headers=self.headers, params=params, timeout=5)
            
            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}: {response.text}")
                
            data = response.json()
            
            # Wait 2 seconds before next API call to avoid rate limiting  
            time.sleep(2)
            
            if 'data' in data and 'value' in data['data']:
                return float(data['data']['value'])
            else:
                raise ValueError(f"Unable to fetch price data for token {token_address}")
                
        except Exception as e:
            logger.error(f"Error fetching current price for {token_address}: {str(e)}")
            raise
    
    def process_candles(self, candles: List[Dict]) -> pd.DataFrame:
        """Convert API response to DataFrame for easy indicator calculation"""
        if not candles:
            raise ValueError("No candle data returned from API")
            
        df = pd.DataFrame(candles)
        
        # Map API column names to standard OHLCV names
        column_mapping = {
            'o': 'open',
            'h': 'high', 
            'l': 'low',
            'c': 'close',
            'v': 'volume'
        }
        
        # Rename columns if they exist
        df = df.rename(columns=column_mapping)
        
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Convert to numeric types
        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['datetime'] = pd.to_datetime(df['unixTime'], unit='s')
        df.set_index('datetime', inplace=True)
        df.sort_index(inplace=True)
        
        # Remove any rows with NaN values
        df = df.dropna()
        
        if df.empty:
            raise ValueError("No valid market data after processing")
            
        return df


class IndicatorCalculator:
    """Technical indicator calculator using pandas and numpy"""
    
    def __init__(self):
        self.cache = {}  # Store historical data for each token
        
    def update_token_data(self, token_symbol: str, token_address: str, fetcher: BirdeyeDataFetcher) -> Dict:
        """Fetch fresh data and calculate all indicators"""
        
        try:
            # Get last 72 hours of data
            df = fetcher.get_historical_hourly(token_address, hours=72)
            
            if df.empty:
                raise ValueError(f"No data available for {token_symbol}")
            
            # Store in cache
            self.cache[token_symbol] = df
            
            # Calculate all indicators
            indicators = self.calculate_all_indicators(df)
            
            # Add metadata
            indicators['token_symbol'] = token_symbol
            indicators['token_address'] = token_address
            indicators['data_points'] = len(df)
            indicators['data_start'] = df.index[0].isoformat()
            indicators['data_end'] = df.index[-1].isoformat()
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error updating token data for {token_symbol}: {str(e)}")
            raise
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate all 6 indicators from hourly data"""
        
        if len(df) < 50:  # Need at least 50 periods for reliable indicators
            logger.warning(f"Only {len(df)} data points available, indicators may be unreliable")
        
        # Get the most recent complete candle
        latest = df.iloc[-1]
        
        try:
            # 1. RSI (14-period)
            rsi = self.calculate_rsi(df['close'], period=14)
            
            # 2. MA Cross (20 and 50)
            ma20 = df['close'].rolling(20).mean().iloc[-1] if len(df) >= 20 else None
            ma50 = df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else None
            ma_cross = 'bull' if ma20 and ma50 and ma20 > ma50 else 'bear' if ma20 and ma50 and ma20 < ma50 else 'neutral'
            
            # 3. Volume Ratio (current vs 24h avg)
            vol_24h_avg = df['volume'].tail(24).mean() if len(df) >= 24 else df['volume'].mean()
            volume_ratio = latest['volume'] / vol_24h_avg if vol_24h_avg > 0 else 1
            
            # 4. ADX (14-period)
            adx = self.calculate_adx(df['high'], df['low'], df['close'], period=14)
            
            # 5. MACD
            macd, signal, histogram = self.calculate_macd(df['close'])
            macd_signal = 'bull' if macd > signal else 'bear' if macd < signal else 'neutral'
            
            # 6. Stochastic Oscillator (14-period)
            stoch_k, stoch_d = self.calculate_stochastic(df['high'], df['low'], df['close'], period=14)
            stoch_signal = 'bull' if stoch_k > stoch_d and stoch_k < 80 else 'bear' if stoch_k < stoch_d and stoch_k > 20 else 'neutral'
            
            return {
                'rsi': round(rsi, 1) if not pd.isna(rsi) else None,
                'ma_cross': ma_cross,
                'ma20': round(ma20, 4) if ma20 and not pd.isna(ma20) else None,
                'ma50': round(ma50, 4) if ma50 and not pd.isna(ma50) else None,
                'volume_ratio': round(volume_ratio, 1),
                'adx': round(adx, 1) if not pd.isna(adx) else None,
                'macd': macd_signal,
                'macd_value': round(macd, 6) if not pd.isna(macd) else None,
                'macd_signal_value': round(signal, 6) if not pd.isna(signal) else None,
                'macd_histogram': round(histogram, 6) if not pd.isna(histogram) else None,
                'stochastic_k': round(stoch_k, 1) if not pd.isna(stoch_k) else None,
                'stochastic_d': round(stoch_d, 1) if not pd.isna(stoch_d) else None,
                'stochastic_signal': stoch_signal,
                'current_price': round(latest['close'], 8),
                'volume_24h': round(df['volume'].tail(24).sum(), 2) if len(df) >= 24 else round(df['volume'].sum(), 2),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            raise
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Simplified ADX calculation"""
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        dm_plus = np.where((high.diff() > low.diff().abs()) & (high.diff() > 0), high.diff(), 0)
        dm_minus = np.where((low.diff().abs() > high.diff()) & (low.diff().abs() > 0), low.diff().abs(), 0)
        
        # Smooth the values
        tr_smooth = pd.Series(true_range).rolling(period).mean()
        dm_plus_smooth = pd.Series(dm_plus).rolling(period).mean()
        dm_minus_smooth = pd.Series(dm_minus).rolling(period).mean()
        
        # Calculate DI+ and DI-
        di_plus = 100 * (dm_plus_smooth / tr_smooth)
        di_minus = 100 * (dm_minus_smooth / tr_smooth)
        
        # Calculate DX
        dx = 100 * (abs(di_plus - di_minus) / (di_plus + di_minus))
        
        # Calculate ADX
        adx = dx.rolling(period).mean()
        return adx.iloc[-1]
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD"""
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14, smooth_k: int = 3) -> tuple:
        """Calculate Stochastic Oscillator using stochastic analysis
        
        The Stochastic Oscillator is based on stochastic calculus principles,
        measuring the momentum of price changes by comparing closing prices
        to their range over a given period.
        
        %K = ((Close - LowestLow) / (HighestHigh - LowestLow)) * 100
        %D = SMA of %K over smooth_k periods
        """
        # Calculate the lowest low and highest high over the period
        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()
        
        # Calculate %K (fast stochastic)
        k_percent = ((close - lowest_low) / (highest_high - lowest_low)) * 100
        
        # Smooth %K to get the final %K line
        k_smoothed = k_percent.rolling(window=smooth_k).mean()
        
        # Calculate %D (slow stochastic) as SMA of %K
        d_percent = k_smoothed.rolling(window=smooth_k).mean()
        
        return k_smoothed.iloc[-1], d_percent.iloc[-1]


async def get_all_token_indicators() -> Dict[str, Dict]:
    """Fetch and calculate indicators for all tokens"""
    
    # Check if API key is set
    if not os.getenv("BIRDEYE_API_KEY"):
        logger.error("BIRDEYE_API_KEY environment variable not set")
        raise ValueError("BIRDEYE_API_KEY not configured")
    
    # Initialize components
    fetcher = BirdeyeDataFetcher()
    calculator = IndicatorCalculator()
    
    results = {}
    errors = {}
    
    for symbol, address in TOKEN_ADDRESSES.items():
        try:
            logger.info(f"Processing {symbol}...")
            
            # Get indicators for this token
            indicators = calculator.update_token_data(symbol, address, fetcher)
            results[symbol] = indicators
            
            logger.info(f"✓ {symbol} completed successfully")
            
        except Exception as e:
            error_msg = f"Error processing {symbol}: {str(e)}"
            logger.error(error_msg)
            errors[symbol] = error_msg
            results[symbol] = None
    
    # Add summary
    results['_summary'] = {
        'total_tokens': len(TOKEN_ADDRESSES),
        'successful': len([v for v in results.values() if v is not None]) - 1,  # -1 for summary
        'failed': len(errors),
        'errors': errors,
        'generated_at': datetime.utcnow().isoformat()
    }
    
    return results