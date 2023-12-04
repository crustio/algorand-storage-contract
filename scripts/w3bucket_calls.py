import sys
sys.path.append('../')

from ast import literal_eval
from contracts.w3bucket.w3bucket import app, BucketEditionParams
import pyteal as pt
from beaker import localnet, client
from algosdk.encoding import decode_address, encode_address, encode_as_bytes
from algosdk.transaction import PaymentTxn, AssetTransferTxn, AssetOptInTxn
from algosdk.atomic_transaction_composer import TransactionWithSigner

app_id=3326
accounts = localnet.kmd.get_accounts()
sender = accounts[0]
mint_acct = accounts[1]

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
            editions = self.client.call(
                "get_bucket_edition_ids",
                boxes=[(self.client.app_id,"edition_ids")],
            ).return_value
            print(f"get bucket editions:{editions} successfully")
        except Exception as e:
            print(f"get bucket editions failed, error:{e}")

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
            self.client.call(
                "set_bucket_edition_prices",
                edition_id=edition_id,
                prices=prices,
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
        metadata_hash,  # 2laYvhe5tGliM1eZd5++yozl1JHA0mJDuv756hg3qdg=
        uri             # ipfs://bafkreihjhjvtbxzxnmlcwkkmeayb72xexxdloybjdj63g5pasfyc7zkvy4
    ):
        try:
            sp = self.client.get_suggested_params()
            sp.flat_fee = True
            sp.fee = 2000 * 4
            ptxn = PaymentTxn(
                sender=mint_acct.address,
                sp=sp,
                receiver=self.client.app_addr,
                amt=10000,
            )
            #ptxn = AssetTransferTxn(
            #    sender.address,
            #    sp,
            #    self.client.app_addr,
            #    0,
            #    110,
            #    #2961,
            #)
            mint_client = client.ApplicationClient(
                client=localnet.get_algod_client(),
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
    app_client = client.ApplicationClient(
        client=localnet.get_algod_client(),
        app=app,
        sender=sender.address,
        signer=sender.signer,
        app_id=app_id,
    )

    w3bucket_client = W3Bucket(app_client)
    args = sys.argv[1:]
    if len(args) == 0:
        print("no command provided, please check help")
        sys.exit()

    match args[0]:
        case 'set_bucket_edition':
            edition = literal_eval(args[2])
            w3bucket_client.set_bucket_edition(int(args[1]),edition)
        case 'get_bucket_edition_ids':
            w3bucket_client.get_bucket_edition_ids(args[1])
        case 'get_bucket_edition':
            w3bucket_client.get_bucket_edition(int(args[1]))
        case 'set_bucket_edition_prices':
            prices = literal_eval(args[2])
            w3bucket_client.set_bucket_edition_prices(int(args[1]), prices)
        case 'get_bucket_edition_prices':
            w3bucket_client.get_bucket_edition_prices(int(args[1]))
        case 'mint':
            w3bucket_client.mint(mint_acct, int(args[1]), args[2], args[3])
        case _:
            print("unexpected command")
