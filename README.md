# Algorand smart contract

## Storage order smart contract

Storage order contract allows users to place storage order on Algorand. Crust storage order [listener](https://github.com/crustio/storage-contract-node) will monitor the order event and place order on Crust network.

### Crust network

Crust network is an incentive layer built on IPFS network. It completes [GPOS](https://wiki.crust.network/docs/en/crustOverview#gpos) and [MPOW](https://wiki.crust.network/docs/en/crustOverview#mpow) mechanisms to build a decentralized storage market([DSM](https://wiki.crust.network/docs/en/crustOverview#dsm)). For more information about Crust network, check this [doc](https://wiki.crust.network/en)

### IPFS gateway

Before using storage order smart contract, make sure you have an IPFS gateway. You can start one on local referring to [this doc](https://docs.ipfs.tech/install/ipfs-desktop/),
or using [public gateways](https://docs.ipfs.tech/concepts/ipfs-gateway/#gateway-providers) or [those](https://github.com/crustio/crust-apps/blob/041258d0aca109a8d5e24cdade0be351c3e57f73/packages/apps-config/src/ipfs-gateway-endpoints/index.ts) maintained by Crust network. You can upload file you want to store to IPFS gateway, it returns a cid(content id) which represents the file and the file size(**Note**: this size stands for the real file size stored on IPFS network, place order with this size rather than the one the file looks like on disk). With these two parameters you can place order on Crust network. Here is an [example](https://wiki.crust.network/docs/en/buildFileStoringWithGWDemo) about how to upload file to Crust IPFS gateway. For more information about IPFS, check this [doc](https://docs.ipfs.tech/).

### Deployment

Run following command to deploy storage order smart contract on Algorand local testnet.
```shell
python3 ./scripts/storage_order_deploy.py
```

### Usage

Functions for contract owner:
1. **add_order_node**: Add storage order merchant node which listens order event and place order on Crust network.
1. **remove_order_node**: Remove storage order merchant node.
1. **set_base_price**: Set base price according to Crust network [base price](https://crust.subscan.io/tools/storage_calculator).
1. **set_byte_price**: Set byte price(set in MB) according to Crust network [byte price](https://crust.subscan.io/tools/storage_calculator).
1. **set_size_limit**: Set file size limit to place order.
1. **set_service_rate**: Set price rate which indicates service price rate.
1. **set_algo_cru_price**: Set CRU and ALGO price based on the real price, which is used to compute file price in ALGO.

Functions for users:
1. **get_price**: Get price in ALGO for file size specified by parameter "size" and for storing permanently or not by parameter "is_permanent".
1. **place_order**: Place order with cid, size and is_permanent with ALGO, payment transaction indicates the price that user should pay for merchant node.

python examples:
```shell
# Note: before you run following commands, set the appId in storage_order_calls.py
# Add merchant order node
python3 ./scripts/storage_order_calls.py add_order_node R52TCLVXRADTZ3X7GTFD675RPIKCE7BR4ZVS2DA6R6YXM53UUCIIZIZN7Y
# Get order price with size:1024Bytes and permanently stored
python3 ./scripts/storage_order_calls.py get_price 7788 True
# Place order, this command will send a transaction with payment whose amount equals to the result of get_price command
python3 ./scripts/storage_order_calls.py place_order bafkreihjhjvtbxzxnmlcwkkmeayb72xexxdloybjdj63g5pasfyc7zkvy4 7788 True
```

## W3Bucket smart contract

This contract is for [CrustCloud](https://crustcloud.io/).

### Deployment

Run following command to deploy W3Bucket smart contract on Algorand local testnet.
```shell
python3 ./scripts/w3bucket_deploy.py
```

### Usage

Functions for contract owner:
1. **set_bucket_edition**: Set bucket edition with id, capacity and max supply number.
1. **set_bucket_edition_prices**: Set bucket edition price which seems like '[(10,100)]'(10 indicates asset id and 100 is the price).
1. **disable_bucket_edition**: Disable indicated bucket edition.
1. **enable_bucket_edition**: Enable indicated bucket edition.

Functions for users:
1. **get_bucket_edition_ids**: Get all bucket edition ids.
1. **get_bucket_edition**: Get indicated bucket edition.
1. **is_active_bucket_edition**: Check if indicated bucket edition is active.
1. **get_bucket_edition_prices**: Get indicated bucket edition prices.
1. **mint**: Mint a bucket with producing a NFT token waiting for claiming.
1. **claim**: Claim minted bucket NFT token, only the account who minted this NFT token can claim.

python examples:
```shell
# Note: before you run following commands, set the appId in w3bucket_calls.py
# Set bucket edition with id=1, capacity=100GB and max minted number=255
python3 ./scripts/w3bucket_calls.py set_bucket_edition 1 '(1,100,255)' 
# Set prices of indicated bucket eidition 1,
# there are two prices: '(0,10000)' indicates asset id equals to '0' which represents native token ALGO here and price 10000, '(1111,1)' indicates asset 1111 with price 1.
python3 ./scripts/w3bucket_calls.py set_bucket_edition_prices 1 '[(0,10000),(1111,1)]'
# Mint a bucket NFT token, with edition=1, asset_id=1111, NFT metdata hash=2laYvhe5tGliM1eZd5++yozl1JHA0mJDuv756hg3qdg=, and asset url=ipfs://bafkreifz3txysww3dynwgfkh3zcbmgizv7ge5gju6ixoj5z2hirrcegvee
# After minting, it will claim the minted bucket NFT token.
python3 ./scripts/w3bucket_calls.py mint 1 1111 '2laYvhe5tGliM1eZd5++yozl1JHA0mJDuv756hg3qdg=' 'ipfs://bafkreifz3txysww3dynwgfkh3zcbmgizv7ge5gju6ixoj5z2hirrcegvee'
```
