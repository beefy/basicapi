from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
import requests
import time
import asyncio
import logging
import threading
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts

from ....models.schemas import WalletBalanceResponse, WalletBalanceItem, TokenBalance, TransactionInfo, TokenChange

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global price cache with threading lock for safety
GLOBAL_PRICE_CACHE = {}
CACHE_EXPIRY_HOURS = 1
CACHE_LOCK = threading.Lock()

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

# Solana RPC endpoint
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"


def create_solana_client() -> Client:
    """Create a Solana client with proper error handling for production environments"""
    try:
        # Try creating client without any additional parameters first
        return Client(SOLANA_RPC_URL)
    except TypeError as e:
        if "proxy" in str(e):
            logger.warning(f"Solana Client proxy parameter issue: {str(e)}. Trying alternative initialization.")
            # If proxy parameter is the issue, try with explicit commitment level only
            from solana.rpc.commitment import Commitment
            try:
                return Client(SOLANA_RPC_URL, commitment=Commitment("confirmed"))
            except Exception:
                # Fallback to basic client
                return Client(SOLANA_RPC_URL)
        else:
            logger.error(f"Unexpected Solana Client initialization error: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Failed to create Solana client: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize Solana client: {str(e)}")


def get_cached_price(token_address: str) -> Optional[float]:
    """Get cached price if it's still valid (within 1 hour)"""
    with CACHE_LOCK:
        if token_address in GLOBAL_PRICE_CACHE:
            cached_data = GLOBAL_PRICE_CACHE[token_address]
            cached_time = cached_data['timestamp']
            cached_price = cached_data['price']
            
            # Check if cache is still valid (within 1 hour)
            if datetime.now() - cached_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                logger.debug(f"Using cached price for {token_address}: ${cached_price}")
                return cached_price
            else:
                # Cache expired, remove it
                logger.debug(f"Cache expired for {token_address}, removing")
                del GLOBAL_PRICE_CACHE[token_address]
        
        return None


def cache_price(token_address: str, price: Optional[float]) -> None:
    """Cache a price with current timestamp"""
    with CACHE_LOCK:
        GLOBAL_PRICE_CACHE[token_address] = {
            'price': price,
            'timestamp': datetime.now()
        }
        logger.debug(f"Cached price for {token_address}: ${price}")


def get_cache_stats() -> Dict:
    """Get cache statistics for monitoring"""
    with CACHE_LOCK:
        total_entries = len(GLOBAL_PRICE_CACHE)
        valid_entries = 0
        expired_entries = 0
        
        cutoff_time = datetime.now() - timedelta(hours=CACHE_EXPIRY_HOURS)
        
        for token_address, cached_data in GLOBAL_PRICE_CACHE.items():
            if cached_data['timestamp'] > cutoff_time:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries, 
            'expired_entries': expired_entries,
            'cache_expiry_hours': CACHE_EXPIRY_HOURS
        }


def cleanup_expired_cache() -> int:
    """Remove expired entries from cache and return number of entries removed"""
    with CACHE_LOCK:
        cutoff_time = datetime.now() - timedelta(hours=CACHE_EXPIRY_HOURS)
        expired_keys = []
        
        for token_address, cached_data in GLOBAL_PRICE_CACHE.items():
            if cached_data['timestamp'] <= cutoff_time:
                expired_keys.append(token_address)
        
        for key in expired_keys:
            del GLOBAL_PRICE_CACHE[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)


class BirdeyeDataFetcher:
    def __init__(self):
        self.api_key = os.getenv("BIRDEYE_API_KEY")
        if not self.api_key:
            logger.warning("BIRDEYE_API_KEY not found in environment variables")
        self.base_url = "https://public-api.birdeye.so"
        self.headers = {"X-API-KEY": self.api_key}
        # Remove the instance cache since we're using global cache now
        
    def get_cache_stats(self):
        """Get cache statistics"""
        return get_cache_stats()
    
    def get_current_price(self, token_address: str) -> Optional[float]:
        """Get current price in USD for a token (with global caching)"""
        # Check global cache first
        cached_price = get_cached_price(token_address)
        if cached_price is not None:
            return cached_price
            
        if not self.api_key:
            logger.warning(f"No API key available for price fetching of {token_address}")
            cache_price(token_address, None)
            return None
            
        url = f"{self.base_url}/defi/price"
        params = {"address": token_address}
        
        try:
            logger.debug(f"Fetching fresh price for {token_address}")
            response = requests.get(url, headers=self.headers, params=params, timeout=5)
            
            if response.status_code != 200:
                logger.warning(f"Birdeye API request failed for {token_address} with status {response.status_code}")
                cache_price(token_address, None)
                return None
                
            data = response.json()
            
            # Reduced wait time to avoid rate limiting
            time.sleep(0.5)
            
            if 'data' in data and 'value' in data['data']:
                price = float(data['data']['value'])
                cache_price(token_address, price)  # Cache the result globally
                logger.info(f"Fetched and cached price for {ADDRESS_TO_SYMBOL.get(token_address, token_address[:8]+'...')}: ${price:.4f}")
                return price
            else:
                logger.warning(f"Unable to fetch price data for token {token_address}")
                cache_price(token_address, None)  # Cache None result
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching price for {token_address}")
            cache_price(token_address, None)
            return None
        except Exception as e:
            logger.error(f"Error fetching price for {token_address}: {str(e)}")
            cache_price(token_address, None)
            return None


def get_sol_balance(wallet_address: str) -> float:
    """Get SOL balance for a given wallet address"""
    try:
        client = create_solana_client()
        response = client.get_balance(Pubkey.from_string(wallet_address))
        
        if hasattr(response, 'value'):
            lamports = response.value
            sol_balance = lamports / 1_000_000_000
            return sol_balance
        else:
            logger.error(f"Invalid response from Solana RPC for wallet {wallet_address[:8]}...")
            raise HTTPException(status_code=400, detail="Invalid response from Solana RPC")
            
    except Exception as e:
        logger.error(f"Error fetching SOL balance for {wallet_address[:8]}...: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error fetching SOL balance: {str(e)}")


def get_crypto_balances(wallet_address: str) -> dict:
    """Get all crypto token balances for a given wallet address"""
    try:
        time.sleep(1)
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
    missing_wallets = []
    
    for i in range(1, 4):
        wallet = os.getenv(f"WALLET{i}")
        if wallet and wallet.strip():
            wallets.append(wallet.strip())
        else:
            missing_wallets.append(f"WALLET{i}")
    
    if missing_wallets:
        logger.warning(f"Missing wallet environment variables: {', '.join(missing_wallets)}")
    
    if not wallets:
        error_msg = f"No wallet addresses found in environment variables ({', '.join(missing_wallets)})"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    logger.info(f"Found {len(wallets)} wallet addresses")
    return wallets


def parse_transaction_details(tx_sig: str, wallet_address: str, client: Client) -> dict:
    """Parse transaction details to extract SOL changes, token changes, and program used"""
    try:
        # Reduced delay to improve performance
        time.sleep(0.1)
        tx = client.get_transaction(tx_sig, max_supported_transaction_version=0)
        
        if not tx.value:
            logger.warning(f"No transaction data found for {tx_sig[:8]}...")
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
        logger.error(f"Error parsing transaction {tx_sig}: {str(e)}")
        return {}


def get_recent_transactions(wallet_address: str, limit: int = 2) -> List[TransactionInfo]:
    """Get recent transactions for a wallet address"""
    try:
        # Reduced delay to improve performance
        time.sleep(0.1)
        client = create_solana_client()
        pubkey = Pubkey.from_string(wallet_address)
        
        # Get recent signatures
        signatures = client.get_signatures_for_address(
            pubkey,
            limit=limit
        )
        
        transactions = []
        for sig in signatures.value:
            # Reduced delay to improve performance
            time.sleep(0.1)
            
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
        logger.error(f"Error fetching transactions for wallet {wallet_address}: {str(e)}")
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
    logger.info("Starting wallet balance fetch")
    
    try:
        wallet_addresses = get_wallet_addresses()
    except HTTPException:
        # Re-raise HTTPExceptions (like missing environment variables)
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting wallet addresses: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load wallet configuration")
    
    # Create a single fetcher instance (using global cache now)
    fetcher = BirdeyeDataFetcher()
    
    # Log cache statistics
    cache_stats = fetcher.get_cache_stats()
    logger.info(f"Price cache stats: {cache_stats['valid_entries']} valid, {cache_stats['expired_entries']} expired out of {cache_stats['total_entries']} total entries")
    
    wallet_items = []
    errors = []
    
    for address in wallet_addresses:
        try:
            logger.info(f"Processing wallet: {address[:8]}...{address[-8:]}")
            balances, total_value, transactions = get_crypto_balances_with_value(address, fetcher)
            
            wallet_items.append(WalletBalanceItem(
                wallet_address=address,
                balances=balances,
                total_usd_value=total_value,
                recent_transactions=transactions
            ))
            
            logger.info(f"Successfully processed wallet {address[:8]}...{address[-8:]} with total value: ${total_value:.2f}")
            
            # Reduced delay between wallets
            if address != wallet_addresses[-1]:  # Don't sleep after the last wallet
                time.sleep(1)
                
        except HTTPException as e:
            # Re-raise HTTPExceptions immediately
            logger.error(f"HTTP error processing wallet {address[:8]}...{address[-8:]}: {e.detail}")
            errors.append(f"Wallet {address[:8]}...{address[-8:]}: {e.detail}")
            
        except Exception as e:
            # Log error but continue with other wallets
            error_msg = f"Error processing wallet {address[:8]}...{address[-8:]}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
    
    # If no wallets were successfully processed, return an error
    if not wallet_items:
        if errors:
            error_detail = f"Failed to process any wallets. Errors: {'; '.join(errors)}"
        else:
            error_detail = "Failed to process any wallets due to unknown errors"
        
        logger.error(error_detail)
        raise HTTPException(status_code=500, detail=error_detail)
    
    # Log warnings if some wallets failed but others succeeded
    if errors:
        logger.warning(f"Some wallets failed to process: {'; '.join(errors)}")
    
    logger.info(f"Successfully processed {len(wallet_items)} out of {len(wallet_addresses)} wallets")
    
    # Log final cache statistics
    final_cache_stats = fetcher.get_cache_stats()
    logger.info(f"Final cache stats: {final_cache_stats['valid_entries']} cached prices available for future requests")
    
    return WalletBalanceResponse(
        wallets=wallet_items,
        timestamp=datetime.utcnow()
    )


@router.get("/cache-stats")
async def get_price_cache_stats():
    """Get statistics about the global price cache"""
    # Clean up expired entries first
    cleanup_expired_cache()
    
    stats = get_cache_stats()
    
    # Add some additional info
    with CACHE_LOCK:
        cached_tokens = []
        for token_address, cached_data in GLOBAL_PRICE_CACHE.items():
            symbol = ADDRESS_TO_SYMBOL.get(token_address, token_address[:8] + '...')
            age_minutes = int((datetime.now() - cached_data['timestamp']).total_seconds() / 60)
            cached_tokens.append({
                'symbol': symbol,
                'price': cached_data['price'],
                'age_minutes': age_minutes
            })
    
    return {
        **stats,
        'cached_tokens': cached_tokens,
        'timestamp': datetime.utcnow()
    }