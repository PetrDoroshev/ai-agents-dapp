import json
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))

with open('./build/contracts/PiContr.json') as f:
    pi_json = json.load(f)
pi_abi = pi_json['abi']
pi_address = pi_json['networks']['5777']['address']
pi_contract = w3.eth.contract(address=pi_address, abi=pi_abi)

with open('./build/contracts/MyToken.json') as f:
    token_json = json.load(f)
token_abi = token_json['abi']
token_address = token_json['networks']['5777']['address']
token_contract = w3.eth.contract(address=token_address, abi=token_abi)

contracts = {
    "pi": pi_contract,
    "token": token_contract
}

# for fn in pi_contract.functions:
#     print(fn.fn_name)