from fastapi import APIRouter, HTTPException
from typing import List, Dict
from datetime import datetime
import os
import requests
import time
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts

from ....models.schemas import WalletBalanceResponse, WalletBalanceItem, TokenBalance

router = APIRouter()

# Token addresses mapping
TOKEN_ADDRESSES = {
    "SOL": "So11111111111111111111111111111111111111112",
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

# Reverse mapping for easy lookup
ADDRESS_TO_SYMBOL = {addr: sym for sym, addr in TOKEN_ADDRESSES.items()}


class BirdeyeDataFetcher:
    def __init__(self):
        self.api_key = os.getenv("BIRDEYE_API_KEY")
        self.base_url = "https://public-api.birdeye.so"
        self.headers = {"X-API-KEY": self.api_key}
    
    def get_current_price(self, token_address: str) -> float:
        """Get current price in USD for a token"""
        url = f"{self.base_url}/defi/price"
        
        params = {"address": token_address}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"API request failed for {token_address} with status {response.status_code}")
                return None
                
            data = response.json()
            
            # Wait to avoid rate limiting
            time.sleep(0.5)
            
            if 'data' in data and 'value' in data['data']:
                return float(data['data']['value'])
            else:
                print(f"Unable to fetch price data for token {token_address}")
                return None
                
        except Exception as e:
            print(f"Error fetching price for {token_address}: {str(e)}")
            return None


def get_sol_balance(wallet_address: str) -> float:
    """Get SOL balance for a given wallet address"""
    try:
        client = Client("https://api.mainnet-beta.solana.com")
        response = client.get_balance(Pubkey.from_string(wallet_address))
        lamports = response.value
        sol_balance = lamports / 1_000_000_000
        return sol_balance
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching SOL balance: {str(e)}")


def get_crypto_balances(wallet_address: str) -> dict:
    """Get all crypto token balances for a given wallet address"""
    try:
        ret = {}
        client = Client("https://api.mainnet-beta.solana.com")

        # Add SOL balance
        ret["So11111111111111111111111111111111111111112"] = get_sol_balance(wallet_address)

        # Get token accounts
        response = client.get_token_accounts_by_owner_json_parsed(
            Pubkey.from_string(wallet_address),
            TokenAccountOpts(program_id=Pubkey.from_string(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # SPL Token Program
            ))
        )

        for account in response.value:
            data = account.account.data.parsed["info"]
            mint = data["mint"]
            amount = int(data["tokenAmount"]["amount"])
            decimals = int(data["tokenAmount"]["decimals"])

            ui_amount = amount / (10 ** decimals)
            ret[mint] = ui_amount

        return ret
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching crypto balances: {str(e)}")


def get_wallet_addresses() -> List[str]:
    """Get the 3 wallet addresses from environment variables"""
    wallets = []
    for i in range(1, 4):
        wallet = os.getenv(f"WALLET{i}")
        if wallet:
            wallets.append(wallet)
    
    if not wallets:
        raise HTTPException(
            status_code=500,
            detail="No wallet addresses found in environment variables (WALLET1, WALLET2, WALLET3)"
        )
    
    return wallets


def get_crypto_balances_with_value(wallet_address: str) -> tuple[Dict[str, TokenBalance], float]:
    """Get crypto balances with USD pricing"""
    fetcher = BirdeyeDataFetcher()
    balances = get_crypto_balances(wallet_address)
    ret = {}
    
    for mint, balance in balances.items():
        usd_price = fetcher.get_current_price(mint)
        usd_value = balance * usd_price if usd_price is not None else None
        
        # Convert mint address to symbol for cleaner output
        symbol = ADDRESS_TO_SYMBOL.get(mint, mint)
        
        ret[symbol] = TokenBalance(
            balance=balance,
            usd_price=usd_price,
            usd_value=usd_value
        )
    
    # Calculate total value
    total_value = sum(
        token.usd_value for token in ret.values() 
        if token.usd_value is not None
    )
    
    return ret, total_value


@router.get("/balances", response_model=WalletBalanceResponse)
async def get_all_wallet_balances():
    """Get all crypto token balances with USD pricing for the 3 configured wallets"""
    wallet_addresses = get_wallet_addresses()
    
    wallet_items = []
    for address in wallet_addresses:
        try:
            balances, total_value = get_crypto_balances_with_value(address)
            wallet_items.append(WalletBalanceItem(
                wallet_address=address,
                balances=balances,
                total_usd_value=total_value
            ))
        except Exception as e:
            # Log error but continue with other wallets
            print(f"Error fetching balances for wallet {address}: {str(e)}")
    
    return WalletBalanceResponse(
        wallets=wallet_items,
        timestamp=datetime.utcnow()
    )