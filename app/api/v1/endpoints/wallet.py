from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import os
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts

from ....models.schemas import WalletBalanceResponse, SolBalanceResponse, WalletBalanceItem, SolBalanceItem

router = APIRouter()


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


@router.get("/balances", response_model=WalletBalanceResponse)
async def get_all_wallet_balances():
    """Get all crypto token balances for the 3 configured wallets"""
    wallet_addresses = get_wallet_addresses()
    
    wallet_items = []
    for address in wallet_addresses:
        try:
            balances = get_crypto_balances(address)
            wallet_items.append(WalletBalanceItem(
                wallet_address=address,
                balances=balances
            ))
        except Exception as e:
            # Log error but continue with other wallets
            print(f"Error fetching balances for wallet {address}: {str(e)}")
    
    return WalletBalanceResponse(
        wallets=wallet_items,
        timestamp=datetime.utcnow()
    )


@router.get("/sol-balance", response_model=SolBalanceResponse)
async def get_all_wallet_sol_balances():
    """Get SOL balance for the 3 configured wallets"""
    wallet_addresses = get_wallet_addresses()
    
    wallet_items = []
    for address in wallet_addresses:
        try:
            sol_balance = get_sol_balance(address)
            wallet_items.append(SolBalanceItem(
                wallet_address=address,
                sol_balance=sol_balance
            ))
        except Exception as e:
            # Log error but continue with other wallets
            print(f"Error fetching SOL balance for wallet {address}: {str(e)}")
    
    return SolBalanceResponse(
        wallets=wallet_items,
        timestamp=datetime.utcnow()
    )