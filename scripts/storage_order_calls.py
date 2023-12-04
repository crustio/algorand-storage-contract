import sys
sys.path.append('../')

from contracts.storage_order.storage_order import app
from beaker import localnet, client
from algosdk.encoding import decode_address, encode_address
from algosdk.transaction import PaymentTxn
from algosdk.atomic_transaction_composer import TransactionWithSigner

app_id=2084

class StorageOrder:
    def __init__(self, client):
        self.client = client

    def get_node_num(self):
        return self.client.get_global_state()['node_num']

    def get_nodes(self):
        node_buf = self.client.get_box_contents(b'nodes')
        i = 0
        nodes = []
        while i < len(node_buf):
            nodes.append(encode_address(node_buf[i:i+32]))
            i += 32
        return nodes

    def get_random_order_node(self):
        try:
            order_node = self.client.call(
                "get_random_order_node",
                boxes=[(self.client.app_id,"nodes")],
            ).return_value
            print(f"get random order node:{order_node} successfully")
        except Exception as e:
            print(f"get random order node failed, error:{e}")

    def add_order_node(self, address):
        try:
            self.client.call(
                "add_order_node",
                boxes=[(self.client.app_id,decode_address(address)),(self.client.app_id,"nodes")],
                address=address,
            )
            print(f"add order node:{args[1]} successfully")
        except Exception as e:
            print(f"add order node:{address} failed, error:{e}")

    def remove_order_node(self, address):
        try:
            self.client.call(
                "remove_order_node",
                boxes=[(self.client.app_id,decode_address(address)),(self.client.app_id,"nodes")],
                address=address,
            )
            print(f"remove order node:{args[1]} successfully")
        except Exception as e:
            print(f"remove order node:{address} failed, error:{e}")

    def get_price(self, size, is_permanent):
        price=self.client.call(
            "get_price",
            size=int(size),
            is_permanent=eval(is_permanent)
        ).return_value
        print(f"get price for size:{args[1]} permanent:{args[2]} is {price}")
        return price

    def get_order_node(self):
        return self.client.call(
            "get_random_order_node",
            boxes=[(self.client.app_id, "nodes")],
        ).return_value

    def place_order(
        self,
        sender,
        cid,
        size,
        is_permanent,
    ):
        try:
            order_node_address=self.get_order_node()
            price=self.get_price(size, is_permanent)
            sp = self.client.get_suggested_params()
            sp.flat_fee = True
            sp.fee = 2000 * 4
            ptxn = PaymentTxn(
                sender.address,
                sp,
                self.client.app_addr,
                price,
            )
            self.client.call(
                "place_order",
                seed=TransactionWithSigner(ptxn, sender.signer),
                merchant=order_node_address,
                cid=cid,
                size=int(size),
                is_permanent=eval(is_permanent),
                boxes=[(self.client.app_id, decode_address(order_node_address)),(self.client.app_id, "nodes")],
            )
            print(f"""
                place order:
                    sender:{sender.address}
                    merchant:{order_node_address}
                    cid:{args[1]},
                    size:{args[2]}, 
                    permanent:{args[3]},
                successfully
            """)
        except Exception as e:
            print(f"place order failed, error:{e}")

if __name__ == '__main__':
    args = sys.argv[1:]
    accounts = localnet.kmd.get_accounts()
    sender = accounts[0]
    order_node = accounts[1]
    app_client = client.ApplicationClient(
        client=localnet.get_algod_client(),
        app=app,
        sender=sender.address,
        signer=sender.signer,
        app_id=app_id,
    )
    storage_client = StorageOrder(app_client)
    if len(args) == 0:
        print("no command provided, please check help")
        sys.exit()
    match args[0]:
        case 'add_order_node':
            storage_client.add_order_node(args[1])
        case 'remove_order_node':
            storage_client.remove_order_node(args[1])
        case 'get_price':
            price=storage_client.get_price(args[1], args[2])
        case 'place_order':
            storage_client.place_order(sender, args[1], args[2], args[3])
        case 'get_node_num':
            print(storage_client.get_node_num())
        case 'get_nodes':
            print(storage_client.get_nodes())
        case 'get_random_order_node':
            storage_client.get_random_order_node()
        case _:
            print("unexpected command")
