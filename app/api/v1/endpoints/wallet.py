from fastapi import APIRouter, HTTPException
from typing import List, Dict
from datetime import datetime
import os
import requests
import time
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts

from ....models.schemas import WalletBalanceResponse, WalletBalanceItem, TokenBalance, TransactionInfo, TokenChange

router = APIRouter()

# Program ID labels for transaction parsing
PROGRAM_LABELS = {
    "11111111111111111111111111111111": "System Program",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "SPL Token",
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "Jupiter",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": "Orca",
    "PhoeNiX1VVeaZrJhLuK2UShigkCwt33AjAk4N6YiWPt": "Phoenix",
}

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
        self._price_cache = {}  # Cache for prices within a single request
    
    def clear_cache(self):
        """Clear the price cache at the start of each request"""
        self._price_cache = {}
    
    def get_current_price(self, token_address: str) -> float:
        """Get current price in USD for a token (with caching)"""
        # Check cache first
        if token_address in self._price_cache:
            return self._price_cache[token_address]
        url = f"{self.base_url}/defi/price"
        
        params = {"address": token_address}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"API request failed for {token_address} with status {response.status_code}")
                return None
                
            data = response.json()
            
            # Wait to avoid rate limiting
            time.sleep(1)
            
            if 'data' in data and 'value' in data['data']:
                price = float(data['data']['value'])
                self._price_cache[token_address] = price  # Cache the result
                return price
            else:
                print(f"Unable to fetch price data for token {token_address}")
                self._price_cache[token_address] = None  # Cache None result
                return None
                
        except Exception as e:
            print(f"Error fetching price for {token_address}: {str(e)}")
            self._price_cache[token_address] = None  # Cache None result
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
        # Add delay before Solana RPC call
        time.sleep(1)
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


def parse_transaction_details(tx_sig: str, wallet_address: str, client: Client) -> dict:
    """Parse transaction details to extract SOL changes, token changes, and program used"""
    try:
        # Add delay before transaction fetch to avoid rate limits
        time.sleep(0.3)
        tx = client.get_transaction(tx_sig, max_supported_transaction_version=0)
        
        if not tx.value:
            print(f"No transaction data found for {tx_sig}")
            return {}
            
        meta = tx.value.transaction.meta
        message = tx.value.transaction.transaction.message
        
        account_keys = message.account_keys
        pre = meta.pre_balances
        post = meta.post_balances
        
        # Find wallet index
        wallet_index = None
        for i, key in enumerate(account_keys):
            if str(key) == wallet_address:
                wallet_index = i
                break
        
        result = {
            'sol_change': None,
            'sol_direction': 'none',
            'token_changes': [],
            'program_used': None,
            'transaction_type': 'other'
        }
        
        # 1. Detect SOL transfers
        if wallet_index is not None:
            sol_change = (post[wallet_index] - pre[wallet_index]) / 1e9
            if abs(sol_change) > 0.0001:  # Ignore tiny fee-level changes
                result['sol_change'] = round(sol_change, 6)
                result['sol_direction'] = 'received' if sol_change > 0 else 'sent'
        
        # 2. Detect token changes
        pre_tokens = meta.pre_token_balances or []
        post_tokens = meta.post_token_balances or []
        
        # Track all tokens that changed for this wallet
        processed_mints = set()
        
        for pre_token in pre_tokens:
            if str(pre_token.owner) == wallet_address:
                mint = str(pre_token.mint)
                if mint in processed_mints:
                    continue
                processed_mints.add(mint)
                
                pre_amt = int(pre_token.ui_token_amount.amount)
                
                post_match = next(
                    (p for p in post_tokens if str(p.mint) == mint and str(p.owner) == wallet_address),
                    None
                )
                
                post_amt = int(post_match.ui_token_amount.amount) if post_match else 0
                decimals = pre_token.ui_token_amount.decimals
                change = (post_amt - pre_amt) / (10 ** decimals)
                
                if abs(change) > 0:
                    symbol = ADDRESS_TO_SYMBOL.get(mint, mint[:8] + '...')
                    result['token_changes'].append({
                        'mint': mint,
                        'symbol': symbol,
                        'change': round(change, 6),
                        'direction': 'received' if change > 0 else 'sent'
                    })
        
        # Check for new tokens (in post but not in pre)
        for post_token in post_tokens:
            if str(post_token.owner) == wallet_address:
                mint = str(post_token.mint)
                if mint in processed_mints:
                    continue
                
                pre_match = next(
                    (p for p in pre_tokens if str(p.mint) == mint and str(p.owner) == wallet_address),
                    None
                )
                
                if not pre_match:
                    post_amt = int(post_token.ui_token_amount.amount)
                    decimals = post_token.ui_token_amount.decimals
                    change = post_amt / (10 ** decimals)
                    
                    if abs(change) > 0:
                        symbol = ADDRESS_TO_SYMBOL.get(mint, mint[:8] + '...')
                        result['token_changes'].append({
                            'mint': mint,
                            'symbol': symbol,
                            'change': round(change, 6),
                            'direction': 'received'
                        })
        
        # 3. Detect program used
        instructions = message.instructions
        for ix in instructions:
            program_id = str(account_keys[ix.program_id_index])
            if program_id in PROGRAM_LABELS:
                result['program_used'] = PROGRAM_LABELS[program_id]
                
                # Determine transaction type
                if 'Jupiter' in result['program_used'] or 'Raydium' in result['program_used'] or 'Orca' in result['program_used']:
                    result['transaction_type'] = 'swap'
                elif 'System Program' in result['program_used'] or 'SPL Token' in result['program_used']:
                    result['transaction_type'] = 'transfer'
                break
        
        return result
        
    except Exception as e:
        print(f"Error parsing transaction {tx_sig}: {str(e)}")
        return {}


def get_recent_transactions(wallet_address: str, limit: int = 2) -> List[TransactionInfo]:
    """Get recent transactions for a wallet address"""
    try:
        # Add delay before Solana RPC call
        time.sleep(0.3)
        client = Client("https://api.mainnet-beta.solana.com")
        pubkey = Pubkey.from_string(wallet_address)
        
        # Get recent signatures
        signatures = client.get_signatures_for_address(
            pubkey,
            limit=limit
        )
        
        transactions = []
        for sig in signatures.value:
            # Add delay before parsing each transaction to avoid rate limits
            time.sleep(0.3)
            
            # Get detailed transaction info
            tx_details = parse_transaction_details(sig.signature, wallet_address, client)
            
            # Convert token_changes to TokenChange objects
            token_changes = [
                TokenChange(**change) for change in tx_details.get('token_changes', [])
            ]
            
            transactions.append(TransactionInfo(
                signature=str(sig.signature),
                block_time=sig.block_time,
                slot=sig.slot,
                confirmation_status=str(sig.confirmation_status),
                sol_change=tx_details.get('sol_change'),
                sol_direction=tx_details.get('sol_direction'),
                token_changes=token_changes,
                program_used=tx_details.get('program_used'),
                transaction_type=tx_details.get('transaction_type')
            ))
        
        return transactions
        
    except Exception as e:
        print(f"Error fetching transactions for wallet {wallet_address}: {str(e)}")
        return []


def get_crypto_balances_with_value(wallet_address: str, fetcher: BirdeyeDataFetcher = None) -> tuple[Dict[str, TokenBalance], float, List[TransactionInfo]]:
    """Get crypto balances with USD pricing"""
    if fetcher is None:
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
    
    # Get recent transactions
    recent_transactions = get_recent_transactions(wallet_address)
    
    return ret, total_value, recent_transactions


@router.get("/balances", response_model=WalletBalanceResponse)
async def get_all_wallet_balances():
    """Get all crypto token balances with USD pricing for the 3 configured wallets"""
    wallet_addresses = get_wallet_addresses()
    
    # Create a single fetcher instance and clear cache for this request
    fetcher = BirdeyeDataFetcher()
    fetcher.clear_cache()
    
    wallet_items = []
    for address in wallet_addresses:
        try:
            balances, total_value, transactions = get_crypto_balances_with_value(address, fetcher)
            print(balances, total_value, transactions)
            wallet_items.append(WalletBalanceItem(
                wallet_address=address,
                balances=balances,
                total_usd_value=total_value,
                recent_transactions=transactions
            ))
            # Add a delay between wallets to prevent rate limiting
            time.sleep(2)
        except Exception as e:
            # Log error but continue with other wallets
            print(f"Error fetching balances for wallet {address}: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
    
    return WalletBalanceResponse(
        wallets=wallet_items,
        timestamp=datetime.utcnow()
    )