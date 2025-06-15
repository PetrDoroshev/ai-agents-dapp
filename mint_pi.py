from web3 import Web3
import json

provider_url = "http://127.0.0.1:7545"

contract_address = input("Введите адресс контракта для токена: ")
owner_address = input("Введите адресс владельца (0 аккаунт): ")
owner_private_key = input("Введите приватный ключ владельца (0 аккаунт): ")
recipient = input("Введите адресс получателя: ")

with open("build/contracts/MyToken.json") as f:
    contract_json = json.load(f)

contract_abi = contract_json['abi']

web3 = Web3(Web3.HTTPProvider(provider_url))
assert web3.is_connected(), "Failed to connect to blockchain"

contract = web3.eth.contract(address=contract_address, abi=contract_abi)

amount = 1000 * 10**18

nonce = web3.eth.get_transaction_count(owner_address)

txn = contract.functions.mint(recipient, amount).build_transaction({
    "from": owner_address,
    "nonce": nonce,
    "gas": 200000,
    "gasPrice": web3.to_wei("20", "gwei")
})

signed_txn = web3.eth.account.sign_transaction(txn, private_key=owner_private_key)
tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

print(f"Minting... tx hash: {tx_hash.hex()}")
receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
print(f"Mint confirmed in block {receipt.blockNumber}")

balance = contract.functions.balanceOf(recipient).call()
print(f"Token balance: {balance} for {recipient}")
