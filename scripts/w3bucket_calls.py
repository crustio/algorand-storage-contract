import sys
sys.path.append('../')

from ast import literal_eval
from contracts.w3bucket.w3bucket import app, BucketEditionParams
import pyteal as pt
from beaker import client
from algosdk.encoding import decode_address, encode_address, encode_as_bytes
from algosdk.transaction import PaymentTxn, AssetTransferTxn, AssetOptInTxn
from algosdk.atomic_transaction_composer import TransactionWithSigner
from utils import get_acct_algod_from_args, network, get_param_or_exit

app_id = int(get_param_or_exit('W3BUCKET_APP_ID'))

class W3Bucket:
    def __init__(self, client):
        self.client = client

    def set_bucket_edition(self, edition_id, edition):
        try:
            print(encode_as_bytes(edition_id))
            self.client.call(
                "set_bucket_edition",
                edition=edition,
                boxes=[(self.client.app_id,encode_as_bytes(edition_id)),(self.client.app_id,"edition_ids")],
            )
            print(f"set bucket editions successfully")
        except Exception as e:
            print(f"set bucket editions failed, error:{e}")

    def get_bucket_edition_ids(self, active):
        try:
            edition_ids = self.client.call(
                "get_bucket_edition_ids",
                boxes=[(self.client.app_id,"edition_ids")],
            ).return_value
            print(f"get bucket edition ids:{edition_ids} successfully")
        except Exception as e:
            print(f"get bucket edition ids failed, error:{e}")

    def disable_bucket_edition(self, edition_id):
        try:
            self.client.call(
                "disable_bucket_edition",
                edition_id=edition_id,
                boxes=[(self.client.app_id,encode_as_bytes(edition_id))],
            ).return_value
            print(f"disable bucket edition:{edition_id} successfully")
        except Exception as e:
            print(f"disable bucket edition:{edition_id} failed, error:{e}")

    def enable_bucket_edition(self, edition_id):
        try:
            self.client.call(
                "enable_bucket_edition",
                edition_id=edition_id,
                boxes=[(self.client.app_id,encode_as_bytes(edition_id))],
            ).return_value
            print(f"enable bucket edition:{edition_id} successfully")
        except Exception as e:
            print(f"enable bucket edition:{edition_id} failed, error:{e}")

    def get_bucket_edition(self, edition_id):
        try:
            editions = self.client.call(
                "get_bucket_edition",
                edition_id=edition_id,
                boxes=[(self.client.app_id,encode_as_bytes(edition_id))],
            ).return_value
            print(f"get bucket editions:{editions} successfully")
        except Exception as e:
            print(f"get bucket editions failed, error:{e}")

    def set_bucket_edition_prices(self, edition_id, prices):
        try:
            assets = []
            for price in prices:
                assets.append(price[0])
            sp = self.client.get_suggested_params()
            sp.flat_fee = True
            sp.fee = 1000 * len(assets)
            self.client.call(
                "set_bucket_edition_prices",
                suggested_params=sp,
                edition_id=edition_id,
                prices=prices,
                foreign_assets=assets,
                boxes=[(self.client.app_id,encode_as_bytes(edition_id))],
            )
            print(f"set bucket edition prices successfully")
        except Exception as e:
            print(f"set bucket edition prices failed, error:{e}")

    def get_bucket_edition_prices(self, edition_id):
        try:
            prices = self.client.call(
                "get_bucket_edition_prices",
                edition_id=edition_id,
                boxes=[(self.client.app_id,encode_as_bytes(edition_id))],
            ).return_value
            print(f"get bucket editions:{prices} successfully")
        except Exception as e:
            print(f"set bucket editions failed, error:{e}")

    def mint(
        self,
        mint_acct,
        edition_id,     # 1
        asset_id,
        metadata_hash,  # 2laYvhe5tGliM1eZd5++yozl1JHA0mJDuv756hg3qdg=
        uri             # ipfs://bafkreihjhjvtbxzxnmlcwkkmeayb72xexxdloybjdj63g5pasfyc7zkvy4
    ):
        try:
            sp = self.client.get_suggested_params()
            sp.flat_fee = True
            sp.fee = 2000
            ptxn = ''
            prices = self.client.call(
                "get_bucket_edition_prices",
                edition_id=edition_id,
                boxes=[(self.client.app_id,encode_as_bytes(edition_id))],
            ).return_value
            asset_price = -1
            for price in prices:
                if price[0] == asset_id:
                    asset_price = price[1]
                    break
            if asset_price == -1:
                print(f'asset id:{asset_id} not supported')
                return
            if asset_id == 0:
                ptxn = PaymentTxn(
                    sender=mint_acct.address,
                    sp=sp,
                    receiver=self.client.app_addr,
                    amt=asset_price,
                )
            else:
                ptxn = AssetTransferTxn(
                    mint_acct.address,
                    sp,
                    self.client.app_addr,
                    asset_price,
                    asset_id,
                )
            mint_client = client.ApplicationClient(
                client=self.client.client,
                app=app,
                sender=mint_acct.address,
                signer=mint_acct.signer,
                app_id=app_id,
            )
            token_id = mint_client.call(
                "mint",
                seed=TransactionWithSigner(ptxn, mint_acct.signer),
                edition_id=edition_id,
                metadata_hash=metadata_hash,
                uri=uri,
                suggested_params=sp,
                boxes=[(self.client.app_id,encode_as_bytes(edition_id))],
            ).return_value
            print(f"token_id:{token_id}")
            print(f"mint successfully")
            mint_client.client.send_transaction(
                AssetOptInTxn(mint_acct.address, sp, token_id).sign(
                    mint_acct.private_key
                )
            )
            mint_client.call(
                "claim",
                token=token_id,
            )
        except Exception as e:
            print(f"mint bucket edition prices failed, error:{e}")

if __name__ == '__main__':
    args = sys.argv[1:]
    (accounts, sender, algod_client) = get_acct_algod_from_args()
    mint_acct = sender
    app_client = client.ApplicationClient(
        client=algod_client,
        app=app,
        sender=sender.address,
        signer=sender.signer,
        app_id=app_id,
    )

    w3bucket_client = W3Bucket(app_client)
    if len(args) == 0:
        print("no command provided, please check help")
        sys.exit()

    print(f"INFO: invoke application on {network}, application id:{app_id}")
    match args[0]:
        case 'set_bucket_edition':
            edition = literal_eval(args[2])
            w3bucket_client.set_bucket_edition(int(args[1]),edition)
        case 'get_bucket_edition_ids':
            w3bucket_client.get_bucket_edition_ids(args[1])
        case 'get_bucket_edition':
            w3bucket_client.get_bucket_edition(int(args[1]))
        case 'enable_bucket_edition':
            w3bucket_client.enable_bucket_edition(int(args[1]))
        case 'disable_bucket_edition':
            w3bucket_client.disable_bucket_edition(int(args[1]))
        case 'set_bucket_edition_prices':
            prices = literal_eval(args[2])
            w3bucket_client.set_bucket_edition_prices(int(args[1]), prices)
        case 'get_bucket_edition_prices':
            w3bucket_client.get_bucket_edition_prices(int(args[1]))
        case 'mint':
            w3bucket_client.mint(mint_acct, int(args[1]), int(args[2]), args[3], args[4])
        case _:
            print("unexpected command")
