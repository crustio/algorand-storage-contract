from typing import Literal
from beaker import Application, GlobalStateValue, Authorize, BuildOptions
from beaker.lib.storage import BoxMapping, BoxList
import pyteal as pt
from beaker.consts import (
    ASSET_MIN_BALANCE,
    BOX_BYTE_MIN_BALANCE,
    BOX_FLAT_MIN_BALANCE,
    FALSE,
    TRUE,
)

PriceItem = pt.abi.StaticBytes[Literal[128]]
MaxEditionNum = 30

class BucketEditionParams(pt.abi.NamedTuple):
    editionId: pt.abi.Field[pt.abi.Uint64]
    capacityInGigabytes: pt.abi.Field[pt.abi.Uint16]
    maxMintableSupply: pt.abi.Field[pt.abi.Uint16]

class BucketEditionItem(pt.abi.NamedTuple):
    maxMintableSupply: pt.abi.Field[pt.abi.Uint16]
    capacityInGigabytes: pt.abi.Field[pt.abi.Uint16]
    currentSupplyMinted: pt.abi.Field[pt.abi.Uint16]
    active: pt.abi.Field[pt.abi.Bool]
    prices: pt.abi.Field[PriceItem]

class BucketEdition(pt.abi.NamedTuple):
    editionId: pt.abi.Field[pt.abi.Uint64]
    active: pt.abi.Field[pt.abi.Bool]
    capacityInGigabytes: pt.abi.Field[pt.abi.Uint16]
    maxMintableSupply: pt.abi.Field[pt.abi.Uint16]
    currentSupplyMinted: pt.abi.Field[pt.abi.Uint16]

class EditionPrice(pt.abi.NamedTuple):
    currency: pt.abi.Field[pt.abi.Uint64]
    price: pt.abi.Field[pt.abi.Uint64]

class W3BucketState:
    min_edition_id = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        default=pt.Int(1),
        descr="Minimum bucket edition id"
    )
    max_edition_id = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        default=pt.Int(100),
        descr="Maximum bucket edition id"
    )
    edition_max_mintable_supply = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        default=pt.Int(1_000_000),
        descr="Upper limit of an bucket edition's maximal mintable supply"
    )
    edition_bucket_id_factor = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        default=pt.Int(1_000_000),
        descr="First bucket id of an edition is: edition_bucket_id_factor * editionId"
    )
    edition_num = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        default=pt.Int(0),
        descr="Edition number"
    )
    editions = BoxMapping(pt.abi.Uint64, BucketEditionItem)
    edition_ids = BoxList(pt.abi.Uint64, MaxEditionNum)

    def __init__(self):
        self.minimum_balance = pt.Int(
            ASSET_MIN_BALANCE
            + (
                BOX_FLAT_MIN_BALANCE
                + (pt.abi.size_of(pt.abi.Uint64) * BOX_BYTE_MIN_BALANCE)
                + (pt.abi.size_of(pt.abi.Uint16) * BOX_BYTE_MIN_BALANCE)
                + (pt.abi.size_of(pt.abi.Uint16) * BOX_BYTE_MIN_BALANCE)
                + (pt.abi.size_of(pt.abi.Uint16) * BOX_BYTE_MIN_BALANCE)
                + (pt.abi.size_of(pt.abi.Uint64) * BOX_BYTE_MIN_BALANCE)
                + (pt.abi.size_of(PriceItem) * BOX_BYTE_MIN_BALANCE)
            )
            * MaxEditionNum
            + (
                BOX_FLAT_MIN_BALANCE
                + (self.edition_ids.box_size.value * BOX_BYTE_MIN_BALANCE)
            )
        )

app = Application(
    "W3Bucket",
    descr="This is web3 bucket contract used to apply storage",
    state=W3BucketState(),
)

@app.create
def create() -> pt.Expr:
    return app.initialize_global_state()

@app.external(authorize=Authorize.only_creator())
def bootstrap(seed: pt.abi.PaymentTransaction) -> pt.Expr:
    return pt.Seq(
        pt.Assert(
            seed.get().receiver() == pt.Global.current_application_address(),
            comment="payment must be to app address",
        ),
        pt.Assert(
            seed.get().amount() >= app.state.minimum_balance,
            comment=f"payment must be for >= {app.state.minimum_balance.value}",
        ),
        pt.Pop(app.state.edition_ids.create()),
    )

@pt.Subroutine(pt.TealType.uint64)
def is_valid(edition: BucketEditionParams) -> pt.Expr:
    return pt.Seq(
        (edition_id := pt.abi.Uint64()).set(edition.editionId),
        (max_supply := pt.abi.Uint16()).set(edition.maxMintableSupply),
        pt.And(
            (edition_id.get() >= app.state.min_edition_id),
            pt.And(
                (edition_id.get() <= app.state.max_edition_id),
                (max_supply.get() <= app.state.edition_max_mintable_supply),
            )
        ),
    )

@pt.Subroutine(pt.TealType.uint64)
def require_active_edition(edition_id: pt.abi.Uint64) -> pt.Expr:
    return pt.Seq(
        pt.Assert(
            app.state.editions[edition_id].exists(),
            comment=f"edition:{edition_id} not exist"
        ),
        (edition := BucketEditionItem()).decode(app.state.editions[edition_id].get()),
        (active := pt.abi.Bool()).set(edition.active),
        active.get() == TRUE,
    )

@pt.ABIReturnSubroutine
def add_edition_id(edition_id: pt.abi.Uint64) -> pt.Expr:
    i = pt.ScratchVar(pt.TealType.uint64)
    return pt.Seq(
        pt.For(i.store(pt.Int(0)),i.load() < app.state.edition_num,i.store(i.load() + pt.Int(1))).Do(
            pt.Seq(
                app.state.edition_ids[i.load()].store_into(_edition_id := pt.abi.Uint64()),
                pt.If(_edition_id.get() == edition_id.get()).Then(pt.Return()),
            )
        ),
        app.state.edition_ids[app.state.edition_num].set(edition_id),
        app.state.edition_num.set(app.state.edition_num + pt.Int(1)),
    )

@pt.ABIReturnSubroutine
def edition_token_minted(edition_id: pt.abi.Uint64) -> pt.Expr:
    return pt.Seq(
        pt.Assert(
            app.state.editions[edition_id].exists(),
            comment=f"edition:{edition_id} not exist"
        ),
        (item := BucketEditionItem()).decode(
            app.state.editions[edition_id].get()
        ),
        (max_supply := pt.abi.Uint16()).set(item.maxMintableSupply),
        (capacity_in_GB := pt.abi.Uint16()).set(item.capacityInGigabytes),
        (supply_minted := pt.abi.Uint16()).set(item.currentSupplyMinted),
        (active := pt.abi.Bool()).set(item.active),
        (prices := pt.abi.make(PriceItem)).set(item.prices),
        supply_minted.set(supply_minted.get() + pt.Int(1)),
        item.set(
            max_supply,
            capacity_in_GB,
            supply_minted,
            active,
            prices,
        ),
        app.state.editions[edition_id].set(item),
    )

@pt.Subroutine(pt.TealType.uint64)
def find_price(
    asset_id: pt.abi.Uint64,
    prices: pt.abi.DynamicArray[EditionPrice]
) -> pt.Expr:
    i = pt.ScratchVar(pt.TealType.uint64)
    return pt.Seq(
        pt.For(i.store(pt.Int(0)), i.load() < prices.length(), i.store(i.load() + pt.Int(1))).Do(
            pt.Seq(
                prices[i.load()].store_into(price := EditionPrice()),
                (i_asset_id := pt.abi.Uint64()).set(price.currency),
                pt.If(asset_id.get() == i_asset_id.get())
                .Then(pt.Return(i.load()))
            )
        ),
        pt.Return(prices.length()),
    )

@pt.Subroutine(pt.TealType.bytes)
def int_2_string(decimal: pt.abi.Uint64) -> pt.Expr:
    return pt.Seq(
        pt.If(decimal.get() == pt.Int(0))
        .Then(pt.Bytes(b'0'))
        .Else(
            pt.Seq(
                (n := pt.abi.Uint64()).set(decimal.get() / pt.Int(10)),
                (t := pt.abi.Uint64()).set(decimal.get() % pt.Int(10) + pt.Btoi(pt.Bytes(b'0'))),
                pt.If(n.get() == pt.Int(0))
                .Then(pt.Itob(t.get()))
                .Else(
                    pt.Concat(
                        int_2_string(n),
                        pt.Itob(t.get())
                    )
                )
            )
        )
    )

@app.external(authorize=Authorize.only_creator())
def set_bucket_edition(
    edition: BucketEditionParams
) -> pt.Expr:
    i = pt.ScratchVar(pt.TealType.uint64)
    prices = pt.abi.make(PriceItem)
    return pt.Seq(
        pt.Assert(
            is_valid(edition),
            comment="Invalid bucket edition"
        ),
        (edition_id := pt.abi.Uint64()).set(edition.editionId),
        (max_supply := pt.abi.Uint16()).set(edition.maxMintableSupply),
        (capacity_in_GB := pt.abi.Uint16()).set(edition.capacityInGigabytes),
        (supply_minted := pt.abi.Uint16()).set(pt.Int(0)),
        pt.If(app.state.editions[edition_id].exists())
        .Then(
            pt.Seq(
                (e := BucketEditionItem()).decode(app.state.editions[edition_id].get()),
                supply_minted.set(e.currentSupplyMinted),
            )
        ),
        (active := pt.abi.Bool()).set(TRUE),
        (edition_item := BucketEditionItem()).set(
            max_supply,
            capacity_in_GB,
            supply_minted,
            active,
            prices,
        ),
        app.state.editions[edition_id].set(edition_item),
        add_edition_id(edition_id),
        pt.Log(
            pt.Concat(
                pt.Bytes("$eventName$EditionUpdated$eventNameEnd$"),
                pt.Bytes("$editionId$"),pt.Itob(edition_id.get()),pt.Bytes("$editionIdEnd$"),
                pt.Bytes("$capacityInGigabytes$"),pt.Itob(capacity_in_GB.get()),pt.Bytes("$capacityInGigabytesEnd$"),
                pt.Bytes("$maxMintableSupply$"),pt.Itob(max_supply.get()),pt.Bytes("$maxMintableSupplyEnd$"),
                pt.Bytes("$blockNumber$"),pt.Itob(pt.Txn.first_valid()),pt.Bytes("$blockNumberEnd$"),
                pt.Bytes("$timestamp$"),pt.Itob(pt.Txn.first_valid_time()),pt.Bytes("$timestampEnd$"),
                pt.Bytes("$transactionIndex$"),pt.Itob(pt.Txn.group_index()),pt.Bytes("$transactionIndexEnd$"),
            )
        ),
    )

@app.external
def get_bucket_edition_ids(
    *,
    output: pt.abi.String
) -> pt.Expr:
    i = pt.ScratchVar(pt.TealType.uint64)
    return pt.Seq(
        (res := pt.abi.make(pt.abi.String)).set(pt.Bytes(b'')),
        pt.For(i.store(pt.Int(0)), i.load() < app.state.edition_num, i.store(i.load() + pt.Int(1))).Do(
            pt.Seq(
                app.state.edition_ids[i.load()].store_into(_id := pt.abi.Uint64()),
                (tmp_array := pt.abi.make(pt.abi.String)).decode(res.encode()),
                res.set(
                    pt.Concat(
                        int_2_string(_id),pt.Bytes(b','),
                        tmp_array.get(),
                    ),
                ),
            )
        ),
        output.set(
            pt.Concat(
                pt.Bytes(b'['),
                pt.Substring(res.get(),pt.Int(0),res.length()-pt.Int(1)),
                pt.Bytes(b']'))
        ),
    )

@app.external
def is_active_bucket_edition(
    edition_id: pt.abi.Uint64,
    *,
    output: pt.abi.Bool
) -> pt.Expr:
    return pt.Seq(
        pt.Assert(
            app.state.editions[edition_id].exists(),
            comment=f"edition:{edition_id} not exist"
        ),
        (edition := BucketEditionItem()).decode(app.state.editions[edition_id].get()),
        (active := pt.abi.Bool()).set(edition.active),
        output.set(active.get() == TRUE),
    )
        

@app.external
def get_bucket_edition(
    edition_id: pt.abi.Uint64,
    *,
    output: BucketEdition
) -> pt.Expr:
    i = pt.ScratchVar(pt.TealType.uint64)
    return pt.Seq(
        (edition := BucketEditionItem()).decode(app.state.editions[edition_id].get()),
        (active := pt.abi.Bool()).set(edition.active),
        (supply_minted := pt.abi.Uint16()).set(edition.currentSupplyMinted),
        pt.If(
            pt.Or(
                active.get(),
                supply_minted.get() > pt.Int(0)
            )
        )
        .Then(
            pt.Seq(
                (capacity_in_GB := pt.abi.Uint16()).set(edition.capacityInGigabytes),
                (max_supply := pt.abi.Uint16()).set(edition.maxMintableSupply),
                (bucket_edition := BucketEdition()).set(
                    edition_id,
                    active,
                    capacity_in_GB,
                    max_supply,
                    supply_minted,
                ),
                output.decode(bucket_edition.encode())
            )
        )
    )

@app.external(authorize=Authorize.only_creator())
def disable_bucket_edition(edition_id: pt.abi.Uint64) -> pt.Expr:
    return pt.Seq(
        pt.Assert(
            app.state.editions[edition_id].exists(),
            comment=f"edition:{edition_id} not exist"
        ),
        (edition := BucketEditionItem()).decode(app.state.editions[edition_id].get()),
        (max_supply := pt.abi.Uint16()).set(edition.maxMintableSupply),
        (capacity_in_GB := pt.abi.Uint16()).set(edition.capacityInGigabytes),
        (supply_minted := pt.abi.Uint16()).set(edition.currentSupplyMinted),
        (active := pt.abi.Bool()).set(FALSE),
        (prices_item := pt.abi.make(PriceItem)).set(edition.prices),
        edition.set(
            max_supply,
            capacity_in_GB,
            supply_minted,
            active,
            prices_item,
        ),
        app.state.editions[edition_id].set(edition),
        pt.Log(
            pt.Concat(
                pt.Bytes("$eventName$EditionActiveUpdated$eventNameEnd$"),
                pt.Bytes("$editionId$"),pt.Itob(edition_id.get()),pt.Bytes("$editionIdEnd$"),
                pt.Bytes("$active$"),pt.Itob(active.get()),pt.Bytes("$activeEnd$"),
                pt.Bytes("$blockNumber$"),pt.Itob(pt.Txn.first_valid()),pt.Bytes("$blockNumberEnd$"),
                pt.Bytes("$timestamp$"),pt.Itob(pt.Txn.first_valid_time()),pt.Bytes("$timestampEnd$"),
                pt.Bytes("$transactionIndex$"),pt.Itob(pt.Txn.group_index()),pt.Bytes("$transactionIndexEnd$"),
            )
        ),
    )

@app.external(authorize=Authorize.only_creator())
def enable_bucket_edition(edition_id: pt.abi.Uint64) -> pt.Expr:
    return pt.Seq(
        pt.Assert(
            app.state.editions[edition_id].exists(),
            comment=f"edition:{edition_id} not exist"
        ),
        (edition := BucketEditionItem()).decode(app.state.editions[edition_id].get()),
        (max_supply := pt.abi.Uint16()).set(edition.maxMintableSupply),
        (capacity_in_GB := pt.abi.Uint16()).set(edition.capacityInGigabytes),
        (supply_minted := pt.abi.Uint16()).set(edition.currentSupplyMinted),
        (active := pt.abi.Bool()).set(TRUE),
        (prices_item := pt.abi.make(PriceItem)).set(edition.prices),
        edition.set(
            max_supply,
            capacity_in_GB,
            supply_minted,
            active,
            prices_item,
        ),
        app.state.editions[edition_id].set(edition),
        pt.Log(
            pt.Concat(
                pt.Bytes("$eventName$EditionActiveUpdated$eventNameEnd$"),
                pt.Bytes("$editionId$"),pt.Itob(edition_id.get()),pt.Bytes("$editionIdEnd$"),
                pt.Bytes("$active$"),pt.Itob(active.get()),pt.Bytes("$activeEnd$"),
                pt.Bytes("$blockNumber$"),pt.Itob(pt.Txn.first_valid()),pt.Bytes("$blockNumberEnd$"),
                pt.Bytes("$timestamp$"),pt.Itob(pt.Txn.first_valid_time()),pt.Bytes("$timestampEnd$"),
                pt.Bytes("$transactionIndex$"),pt.Itob(pt.Txn.group_index()),pt.Bytes("$transactionIndexEnd$"),
            )
        ),
    )

@app.external(authorize=Authorize.only_creator())
def set_bucket_edition_prices(
    edition_id: pt.abi.Uint64,
    prices: pt.abi.DynamicArray[EditionPrice]
) -> pt.Expr:
    i = pt.ScratchVar(pt.TealType.uint64)
    return pt.Seq(
        pt.Assert(
            require_active_edition(edition_id),
            comment=f"edition:{edition_id} is not active or existed"
        ),
        (price_bytes := pt.abi.String()).set(prices.encode()),
        pt.Assert(
            price_bytes.length() < pt.Int(pt.abi.size_of(PriceItem)),
            comment=f"prices:{price_bytes.length()} size exceed limit:{pt.abi.size_of(PriceItem)}"
        ),
        (edition := BucketEditionItem()).decode(app.state.editions[edition_id].get()),
        (max_supply := pt.abi.Uint16()).set(edition.maxMintableSupply),
        (capacity_in_GB := pt.abi.Uint16()).set(edition.capacityInGigabytes),
        (supply_minted := pt.abi.Uint16()).set(edition.currentSupplyMinted),
        (active := pt.abi.Bool()).set(edition.active),
        (prices_item := pt.abi.make(PriceItem)).decode(prices.encode()),
        edition.set(
            max_supply,
            capacity_in_GB,
            supply_minted,
            active,
            prices_item,
        ),
        app.state.editions[edition_id].set(edition),
        price_bytes.set(pt.Bytes(b'')),
        pt.For(i.store(pt.Int(0)), i.load() < prices.length(), i.store(i.load() + pt.Int(1))).Do(
            pt.Seq(
                prices[i.load()].store_into(edition_price := EditionPrice()),
                (asset_id := pt.abi.Uint64()).set(edition_price.currency),
                (price := pt.abi.Uint64()).set(edition_price.price),
                (tmp_str := pt.abi.make(pt.abi.String)).decode(price_bytes.encode()),
                price_bytes.set(
                    pt.Concat(
                        tmp_str.get(),
                        pt.Itob(asset_id.get()),
                        pt.Bytes(b','),
                        pt.Itob(price.get()),
                        pt.Bytes(b';'),
                    )
                )
            )
        ),
        pt.Log(
            pt.Concat(
                pt.Bytes("$eventName$EditionPriceUpdated$eventNameEnd$"),
                pt.Bytes("$editionId$"),pt.Itob(edition_id.get()),pt.Bytes("$editionIdEnd$"),
                pt.Bytes("$prices$"),pt.Substring(price_bytes.get(),pt.Int(0),price_bytes.length()-pt.Int(1)),pt.Bytes("$pricesEnd$"),
                pt.Bytes("$blockNumber$"),pt.Itob(pt.Txn.first_valid()),pt.Bytes("$blockNumberEnd$"),
                pt.Bytes("$timestamp$"),pt.Itob(pt.Txn.first_valid_time()),pt.Bytes("$timestampEnd$"),
                pt.Bytes("$transactionIndex$"),pt.Itob(pt.Txn.group_index()),pt.Bytes("$transactionIndexEnd$"),
            )
        ),
    )

@app.external
def get_bucket_edition_prices(
    edition_id: pt.abi.Uint64,
    *,
    output: pt.abi.DynamicArray[EditionPrice]
) -> pt.Expr:
    return pt.Seq(
        pt.Assert(
            require_active_edition(edition_id),
            comment=f"edition:{edition_id} is not active or existed"
        ),
        (edition := BucketEditionItem()).decode(app.state.editions[edition_id].get()),
        (prices := pt.abi.make(PriceItem)).set(edition.prices),
        output.decode(prices.get()),
    )

@app.external
def mint(
    seed: pt.abi.Transaction,
    edition_id: pt.abi.Uint64,
    metadata_hash: pt.abi.String,
    uri: pt.abi.String,
    *,
    output: pt.abi.Uint64,
) -> pt.Expr:
    return pt.Seq(
        (t := pt.abi.String()).set(seed.get().type()),
        pt.Assert(
            pt.Or(t.get() == pt.Bytes(b'pay'), t.get() == pt.Bytes(b'axfer')),
            comment=f"Transfer type must be pay or axfer"
        ),
        pt.Assert(
            pt.Or(
                seed.get().receiver() == pt.Global.current_application_address(),
                seed.get().asset_receiver() == pt.Global.current_application_address(),
            ),
            comment="payment receiver:{seed.get().receiver()} must be to app address",
        ),
        pt.Assert(
            require_active_edition(edition_id),
            comment=f"edition:{edition_id} is not active or existed"
        ),
        (item := BucketEditionItem()).decode(app.state.editions[edition_id].get()),
        (max_supply := pt.abi.Uint16()).set(item.maxMintableSupply),
        (supply_minted := pt.abi.Uint16()).set(item.currentSupplyMinted),
        (capacity_in_GB := pt.abi.Uint16()).set(item.capacityInGigabytes),
        (price_bytes := pt.abi.make(PriceItem)).set(item.prices),
        pt.Assert(
            supply_minted.get() < max_supply.get(),
            comment="Exceed max mintable supply"
        ),
        (prices := pt.abi.make(pt.abi.DynamicArray[EditionPrice])).decode(price_bytes.encode()),
        (asset_id := pt.abi.Uint64()).set(seed.get().xfer_asset()),
        (index := pt.abi.Uint64()).set(find_price(asset_id, prices)),
        pt.Assert(
            index.get() < prices.length(),
            comment=f"Invaid asset",
        ),
        prices[index.get()].store_into(price_item := EditionPrice()),
        (price := pt.abi.Uint64()).set(price_item.price),
        pt.If(asset_id.get() == pt.Int(0))
        .Then(
            pt.Seq(
                pt.Assert(
                    seed.get().amount() >= price.get(),
                    comment=f"Must send required price",
                ),
                (exceed := pt.abi.Uint64()).set(seed.get().amount() - price.get()),
                pt.If(exceed.get() > pt.Int(0))
                .Then(
                    pt.InnerTxnBuilder.Execute(
                        {
                            pt.TxnField.type_enum: pt.TxnType.Payment,
                            pt.TxnField.amount: exceed.get(),
                            pt.TxnField.receiver: pt.Txn.sender(),
                        }
                    )
                )
            )
        )
        .Else(
            pt.Seq(
                pt.Assert(
                    seed.get().asset_amount() >= price.get(),
                    comment=f"Must send required price",
                ),
                (exceed := pt.abi.Uint64()).set(seed.get().asset_amount() - price.get()),
                pt.If(exceed.get() > pt.Int(0))
                .Then(
                    pt.InnerTxnBuilder.Execute(
                        {
                            pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
                            pt.TxnField.xfer_asset: asset_id.get(),
                            pt.TxnField.asset_amount: exceed.get(),
                            pt.TxnField.asset_receiver: pt.Txn.sender(),
                            pt.TxnField.fee: pt.Int(0),
                            pt.TxnField.asset_sender: pt.Global.current_application_address(),
                        }
                    ),
                )
            )
        ),
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetConfig,
                pt.TxnField.config_asset_name: pt.Bytes(b'W3Bucket'),
                pt.TxnField.config_asset_unit_name: pt.Bytes(b'W3BKT'),
                pt.TxnField.config_asset_metadata_hash: pt.Base64Decode.std(metadata_hash.get()),
                pt.TxnField.config_asset_total: pt.Int(1),
                pt.TxnField.config_asset_decimals: pt.Int(0),
                pt.TxnField.config_asset_default_frozen: pt.Int(0),
                pt.TxnField.config_asset_reserve: pt.Txn.sender(),
                pt.TxnField.config_asset_clawback: pt.Global.current_application_address(),
                pt.TxnField.config_asset_url: uri.get(),
                pt.TxnField.fee: pt.Int(0),
            }
        ),
        (token_id := pt.abi.Uint64()).set(pt.InnerTxn.created_asset_id()),
        output.set(token_id),
        edition_token_minted(edition_id),
        pt.Log(
            pt.Concat(
                pt.Bytes("$eventName$BucketMinted$eventNameEnd$"),
                pt.Bytes("$to$"),pt.Txn.sender(),pt.Bytes("$toEnd$"),
                pt.Bytes("$editionId$"),pt.Itob(edition_id.get()),pt.Bytes("$editionIdEnd$"),
                pt.Bytes("$tokenId$"),pt.Itob(token_id.get()),pt.Bytes("$tokenIdEnd$"),
                pt.Bytes("$tokenURI$"),uri.get(),pt.Bytes("$tokenURIEnd$"),
                pt.Bytes("$capacityInGigabytes$"),pt.Itob(capacity_in_GB.get()),pt.Bytes("$capacityInGigabytesEnd$"),
                pt.Bytes("$currency$"),pt.Itob(asset_id.get()),pt.Bytes("$currencyEnd$"),
                pt.Bytes("$price$"),pt.Itob(price.get()),pt.Bytes("$priceEnd$"),
                pt.Bytes("$blockNumber$"),pt.Itob(pt.Txn.first_valid()),pt.Bytes("$blockNumberEnd$"),
                pt.Bytes("$timestamp$"),pt.Itob(pt.Txn.first_valid_time()),pt.Bytes("$timestampEnd$"),
                pt.Bytes("$transactionIndex$"),pt.Itob(pt.Txn.group_index()),pt.Bytes("$transactionIndexEnd$"),
            )
        ),
    )

@app.external
def claim(
    token: pt.abi.Asset
) -> pt.Expr:
    return pt.Seq(
        app_bal := token.holding(pt.Global.current_application_address()).balance(),
        pt.Assert(
            app_bal.value() == pt.Int(1),
            comment=f"No such token minted or has been transferred"
        ),
        reserve_address := pt.AssetParam.reserve(token.asset_id()),
        pt.Assert(
            reserve_address.hasValue(),
            comment=f"Invalid asset:{token.asset_id()}",
        ),
        pt.Assert(
            reserve_address.value() == pt.Txn.sender(),
            comment=f"Incorrect claim account",
        ),
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
                pt.TxnField.xfer_asset: token.asset_id(),
                pt.TxnField.asset_amount: pt.Int(1),
                pt.TxnField.asset_receiver: pt.Txn.sender(),
                pt.TxnField.asset_sender: pt.Global.current_application_address(),
                pt.TxnField.fee: pt.Int(1000),
            }
        ),
    )

app.build().export("./artifacts/w3bucket")
