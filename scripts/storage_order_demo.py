import sys
from algosdk import account, mnemonic
from nacl.signing import SigningKey
import base64

# 1. Construct auth header
args = sys.argv[1:]
mn = args[0]
pk = mnemonic.to_private_key(mn)
addr = account.address_from_private_key(pk)
sk = list(base64.b64decode(pk))
sig_hex = f"0x{SigningKey(bytes(sk[:32])).sign(addr.encode()).signature.hex()}"
authHeader = base64.b64encode(f"sub-{addr}:{sig_hex}".encode('utf-8')).decode('utf-8')

import requests
import json

# IPFS Web3 Authed Gateway address
ipfsGateway = "https://gw-seattle.crustcloud.io"

# 2. Create ipfs http client
headers = { "Authorization" : f"Basic {authHeader}" }
files = {'upload_file': open('./utils.py','rb')}
res = requests.post(f"{ipfsGateway}/api/v0/add", files=files, headers=headers)
res_json = json.loads(res.text)
cid = res_json['Hash']
size = int(res_json['Size'])

print(f"Upload file to IPFS successfully, cid:{res_json['Hash']},size:{res_json['Size']}")

sys.path.append('../')
from contracts.storage_order.storage_order import app
from beaker import client, localnet
from algosdk.v2client import algod

# 3. Get algod application client
app_id = 1275319623
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
algod_address = "https://mainnet-api.algonode.cloud"
algod_client = algod.AlgodClient(algod_token=algod_token,algod_address=algod_address)
account = localnet.kmd.LocalAccount(address=addr,private_key=pk)
app_client = client.ApplicationClient(
  client=algod_client,
  app=app,
  sender=account.address,
  signer=account.signer,
  app_id=app_id
)

# 4. Get price
is_permanent = False
price = app_client.call(
  "get_price",
  size=size,
  is_permanent=is_permanent
).return_value
print(f"Get price successfully, price:{price}, is_permanent:{is_permanent}")

from beaker import client
from algosdk.encoding import decode_address
from algosdk.transaction import PaymentTxn
from algosdk.atomic_transaction_composer import TransactionWithSigner

# 5. Get order node to place order
order_node_address = app_client.call(
  "get_random_order_node",
  boxes=[(app_client.app_id, "nodes")]
).return_value

# 6. Place order
sp = app_client.get_suggested_params()
sp.flat_fee = True
sp.fee = 2000 * 4
ptxn = PaymentTxn(
  account.address,
  sp,
  app_client.app_addr,
  price,
)
app_client.call(
  "place_order",
  seed=TransactionWithSigner(ptxn, account.signer),
  merchant=order_node_address,
  cid=cid,
  size=size,
  is_permanent=is_permanent,
  boxes=[(app_client.app_id, decode_address(order_node_address)),(app_client.app_id, "nodes")],
)
print(f"Place order cid:{cid}, size:{size}, is_permanent:{is_permanent} successfully!")
