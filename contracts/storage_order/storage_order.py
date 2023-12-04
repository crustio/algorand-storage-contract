from beaker import Application, GlobalStateValue, Authorize, BuildOptions
from beaker.lib.storage import BoxMapping, BoxList
import pyteal as pt
from beaker.consts import (
    BOX_BYTE_MIN_BALANCE,
    BOX_FLAT_MIN_BALANCE,
)

class StorageOrderState:
    base_price = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="Storage order base price per file"
    )
    byte_price = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="Storage order byte price"
    )
    size_limit = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="File size limit"
    )
    service_rate = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="Service rate for the real place order node"
    )
    algo_price = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="ALGO price"
    )
    cru_price = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="CRU price"
    )
    node_num = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        default=pt.Int(0),
        descr="Order node number"
    )
    nodes=BoxList(pt.abi.Address, 30)

    def __init__(self):
        self.minimum_balance = pt.Int(
            BOX_FLAT_MIN_BALANCE
            + (self.nodes.box_size.value * BOX_BYTE_MIN_BALANCE)
        )

app = Application(
    "StorageOrder",
    descr="This is storage order contract used to place order",
    state=StorageOrderState(),
)

@app.create
def create() -> pt.Expr:
    return app.initialize_global_state()

@app.external(authorize=Authorize.only_creator())
def bootstrap(
    seed: pt.abi.PaymentTransaction,
    base_price: pt.abi.Uint64,
    byte_price: pt.abi.Uint64,
    size_limit: pt.abi.Uint64,
    service_rate: pt.abi.Uint64,
    algo_price: pt.abi.Uint64,
    cru_price: pt.abi.Uint64
) -> pt.Expr:
    return pt.Seq(
        pt.Assert(
            seed.get().receiver() == pt.Global.current_application_address(),
            comment="payment must be to app address",
        ),
        pt.Assert(
            seed.get().amount() >= app.state.minimum_balance,
            comment=f"payment must be for >= {app.state.minimum_balance.value}",
        ),
        pt.Pop(app.state.nodes.create()),
        app.state.base_price.set(base_price.get()),
        app.state.byte_price.set(byte_price.get()),
        app.state.size_limit.set(size_limit.get()),
        app.state.service_rate.set(service_rate.get()),
        app.state.algo_price.set(algo_price.get()),
        app.state.cru_price.set(cru_price.get()),
    )

@app.external(authorize=Authorize.only_creator())
def set_base_price(price: pt.abi.Uint64) -> pt.Expr:
    return app.state.base_price.set(price.get())

@app.external(authorize=Authorize.only_creator())
def set_byte_price(price: pt.abi.Uint64) -> pt.Expr:
    return app.state.byte_price.set(price.get())

@app.external(authorize=Authorize.only_creator())
def set_size_limit(size: pt.abi.Uint64) -> pt.Expr:
    return app.state.size_limit.set(size.get())

@app.external(authorize=Authorize.only_creator())
def set_service_rate(rate: pt.abi.Uint64) -> pt.Expr:
    return app.state.service_rate.set(rate.get())

@app.external(authorize=Authorize.only_creator())
def set_algo_cru_price(algo_price: pt.abi.Uint64, cru_price: pt.abi.Uint64) -> pt.Expr:
    return pt.Seq(
        app.state.algo_price.set(algo_price.get()),
        app.state.cru_price.set(cru_price.get())
    )

@app.external(authorize=Authorize.only_creator())
def add_order_node(address: pt.abi.Address) -> pt.Expr:
    return pt.Seq(
        pt.Assert(
            app.state.node_num < app.state.nodes.elements,
            comment=f"order node number has exceeded limit:{app.state.nodes.elements}",
        ),
        pt.Assert(
            pt.Not(_address_exist(address)),
            comment=f"{address} has been added",
        ),
        app.state.nodes[app.state.node_num].set(address),
        app.state.node_num.set(app.state.node_num + pt.Int(1)),
    )

@app.external(authorize=Authorize.only_creator())
def remove_order_node(address: pt.abi.Address) -> pt.Expr:
    last_address = pt.abi.Address()
    deleted_position = pt.ScratchVar(pt.TealType.uint64)
    return pt.Seq(
        pt.Assert(
            app.state.node_num > pt.Int(0),
            comment="no node to remove",
        ),
        deleted_position.store(_find_position(address)),
        pt.Assert(
            deleted_position.load() < app.state.node_num,
            comment=f"order node:{address} not exist",
        ),
        pt.If(app.state.node_num == pt.Int(1))
        .Then(
            app.state.node_num.set(pt.Int(0))
        )
        .Else(
            pt.Seq(
                app.state.nodes[app.state.node_num - pt.Int(1)].store_into(last_address),
                app.state.nodes[deleted_position.load()].set(last_address),
                app.state.node_num.set(app.state.node_num - pt.Int(1)),
            )
        ),
    )

@app.external(read_only=True)
def get_random_order_node(*, output: pt.abi.Address) -> pt.Expr:
    return pt.Seq(
        pt.Assert(
            app.state.node_num > pt.Int(0),
            comment="no node to order",
        ),
        output.set(app.state.nodes[pt.Global.latest_timestamp() % app.state.node_num].get()),
    )

@app.external(read_only=True)
def get_price(
    size: pt.abi.Uint64,
    is_permanent: pt.abi.Bool,
    *,
    output: pt.abi.Uint64
) -> pt.Expr:
    return output.set(_get_price(size, is_permanent))

@app.external
def place_order(
    seed: pt.abi.PaymentTransaction,
    merchant: pt.abi.Account,
    cid: pt.abi.String,
    size: pt.abi.Uint64,
    is_permanent: pt.abi.Bool
) -> pt.Expr:
    price = pt.ScratchVar(pt.TealType.uint64)
    return pt.Seq(
        pt.Assert(
            seed.get().receiver() == pt.Global.current_application_address(),
            comment="payment must be to app address",
        ),
        pt.Assert(
            app.state.node_num > pt.Int(0),
            comment="no node to order",
        ),
        (merchant_addr := pt.abi.Address()).set(merchant.address()),
        pt.Assert(
            _address_exist(merchant_addr),
            comment=f"{merchant_addr.get()} is not an order node",
        ),
        pt.Assert(
            size.get() <= app.state.size_limit,
            comment=f"given file size:{size.get()} exceeds size limit:{app.state.size_limit}"
        ),
        price.store(_get_price(size, is_permanent)),
        pt.Assert(
            seed.get().amount() >= price.load(),
            comment=f"payment must be for >= {app.state.minimum_balance.value}",
        ),
        # Pay to merchant
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.Payment,
                pt.TxnField.amount: price.load(),
                pt.TxnField.receiver: merchant_addr.get(),
            }
        ),
        # Refund exceeded fee to customer
        pt.If(seed.get().amount() - price.load() > pt.Int(0))
        .Then(
            pt.InnerTxnBuilder.Execute(
                {
                    pt.TxnField.type_enum: pt.TxnType.Payment,
                    pt.TxnField.amount: seed.get().amount() - price.load(),
                    pt.TxnField.receiver: pt.Txn.sender(),
                }
            )
        ),
        pt.Log(
            pt.Concat(
                pt.Bytes("$event_name$PlaceOrder$event_name_end$"),
                pt.Bytes("$customer$"),pt.Txn.sender(),pt.Bytes("$customer_end$"),
                pt.Bytes("$merchant$"),merchant_addr.get(),pt.Bytes("$merchant_end$"),
                pt.Bytes("$cid$"),cid.get(),pt.Bytes("$cid_end$"),
                pt.Bytes("$size$"),pt.Itob(size.get()),pt.Bytes("$size_end$"),
                pt.Bytes("$price$"),pt.Itob(price.load()),pt.Bytes("$price_end$"),
                pt.Bytes("$is_permanent$"),pt.Itob(is_permanent.get()),pt.Bytes("$is_permanent_end$"),
            )
        ),
    )

@pt.Subroutine(pt.TealType.uint64)
def _get_price(size: pt.abi.Uint64, is_permanent: pt.abi.Bool) -> pt.Expr:
    price = pt.ScratchVar(pt.TealType.uint64)
    return pt.Seq(
        price.store(
            (app.state.base_price + size.get() * app.state.byte_price / pt.Int(1024) / pt.Int(1024)) 
            * (app.state.service_rate + pt.Int(100)) / pt.Int(100) * app.state.cru_price / app.state.algo_price / pt.Int(10**12)
        ),
        pt.If(is_permanent.get())
        .Then(price.load() * pt.Int(200))
        .Else(price.load())
    )

@pt.Subroutine(pt.TealType.uint64)
def _find_position(address: pt.abi.Address) -> pt.Expr:
    i=pt.ScratchVar(pt.TealType.uint64)
    return pt.Seq(
        (index := pt.abi.Uint64()).set(app.state.node_num),
        pt.For(i.store(pt.Int(0)), i.load() < app.state.node_num, i.store(i.load()+pt.Int(1))).Do(
            pt.If(address.get() == app.state.nodes[i.load()].get())
            .Then(
                pt.Seq(
                    index.set(i.load()),
                    pt.Break(),
                )
            )
        ),
        index.get(),
    )

@pt.Subroutine(pt.TealType.uint64)
def _address_exist(address: pt.abi.Address) -> pt.Expr:
    return app.state.node_num - _find_position(address)

app.build().export("./artifacts/storage_order")
