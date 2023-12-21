import sys
import os
from algosdk.v2client import algod
from beaker import localnet
from algosdk import account, mnemonic
from dotenv import load_dotenv

def get_param_or_exit(name):
    val = os.getenv(name)
    if val == None or val == '':
        print(f"ERROR: {name} not provided, please set it in .env")
        sys.exit()
    return val

load_dotenv()
network = os.getenv('NETWORK',default='localnet')
algod_token = get_param_or_exit('ALGOD_TOKEN')

def get_local_client():
    return localnet.get_algod_client()

def get_local_accounts():
    return localnet.kmd.get_accounts()

def get_testnet_client():
    url = get_param_or_exit('ALGOD_TESTNET_URL')
    return algod.AlgodClient(algod_token=algod_token, algod_address=url)

def get_mainnet_client():
    url = get_param_or_exit('ALGOD_MAINNET_URL')
    return algod.AlgodClient(algod_token=algod_token, algod_address=url)

def get_account_from_mnemonic():
    mn = get_param_or_exit('MNEMONIC')
    pk = mnemonic.to_private_key(mn)
    addr = account.address_from_private_key(pk)
    return localnet.kmd.LocalAccount(address=addr, private_key=pk)

def get_acct_algod_from_args():
    accounts = []
    if network == 'localnet':
        accounts = localnet.kmd.get_accounts()
        sender = accounts[0]
        algod_client = get_local_client()
    elif network == 'testnet':
        sender = get_account_from_mnemonic()
        algod_client = get_testnet_client()
    elif network == 'mainnet':
        sender = get_account_from_mnemonic()
        algod_client = get_mainnet_client()
    return accounts, sender, algod_client
