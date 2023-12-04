import sys
sys.path.append('../')

from contracts.storage_order.storage_order import app
from beaker import localnet, client
from algosdk.transaction import PaymentTxn
from algosdk.atomic_transaction_composer import TransactionWithSigner

accounts = localnet.kmd.get_accounts()
sender = accounts[0]
order_node = accounts[1]

app_client = client.ApplicationClient(
    client=localnet.get_algod_client(),
    app=app,
    sender=sender.address,
    signer=sender.signer,
)

app_id, app_addr, txid = app_client.create()
print(
    f"""
Deployed app in txid {txid}
App ID: {app_id}
App Address: {app_addr}
Deploy storage order smart contract successfully!
"""
)

print(localnet.get_algod_client())

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
    base_price=1000000000000000,
    byte_price=100000000000,
    size_limit=209715200,
    service_rate=30,
    algo_price=110,
    cru_price=590,
    boxes=[(app_client.app_id, "nodes")],
)
