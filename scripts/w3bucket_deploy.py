import sys
sys.path.append('../')

from contracts.w3bucket.w3bucket import app, BucketEditionParams
from beaker import localnet, client
from algosdk.transaction import PaymentTxn
from algosdk.atomic_transaction_composer import TransactionWithSigner
from utils import get_acct_algod_from_args, network

(accounts, sender, algod_client) = get_acct_algod_from_args()

app_client = client.ApplicationClient(
    client=algod_client,
    app=app,
    sender=sender.address,
    signer=sender.signer,
)

app_id, app_addr, txid = app_client.create()
print(
    f"""
Deployed app in txid {txid} to {network}
App ID: {app_id}
App Address: {app_addr}
Deploy storage order smart contract successfully!
"""
)

print(algod_client)

sp = app_client.get_suggested_params()
sp.flat_fee = True
sp.fee = 4000
ptxn = PaymentTxn(
    sender.address,
    sp,
    app_client.app_addr,
    app.state.minimum_balance.value * 2,
)
app_client.call(
    "bootstrap",
    seed=TransactionWithSigner(ptxn, sender.signer),
    boxes=[(app_client.app_id, "edition_ids")],
)
