import variables
from app.ai_models.models import execute_style_transfer, execute_object_detection
from app.contracts import token_contract, pi_contract, w3, token_address, pi_address

from web3 import Web3

async def process_ai_task(
    run_id: str,
    job_id: str,
    input_path: str,
    requester: str,
    random_state: str
):
    try:
        new_input_path = f"./app/uploads/{input_path}"
        file_name_wo_ext = "".join("".join(input_path.split("/")[-1:]).split(".")[:-1])
        new_output_path = f"./app/downloads/{file_name_wo_ext}"

        print(new_input_path)
        print(new_output_path)

        if job_id == "style":
            success = await execute_style_transfer(new_input_path, new_output_path)
        elif job_id == "detect":
            success = await execute_object_detection(new_input_path, new_output_path)
        else:
            success = False
        
        if success:
            output_path = success.split("/")[-1]
            with open(f"./app/downloads/{output_path}", "rb") as f:
                output_hash = Web3.keccak(f.read())
            
            # Update blockchain with results
            nonce = w3.eth.get_transaction_count(variables.OWNER_ADDRESS)
            gas_price = w3.eth.gas_price
            
            txn = pi_contract.functions.submitRunResult(
                run_id,
                f"/downloads/{output_path}",
                Web3.keccak(open(f"./app/downloads/{output_path}", "rb").read()),
                1
            ).build_transaction({
                'from': variables.OWNER_ADDRESS,
                'nonce': nonce,
                'gas': 800_000,
                'gasPrice': gas_price,
            })
            
            signed_txn = w3.eth.account.sign_transaction(txn, private_key=variables.OWNER_PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"Run {run_id} completed successfully. TX hash: {tx_hash.hex()}")
        else:
            nonce = w3.eth.get_transaction_count(variables.OWNER_ADDRESS)
            gas_price = w3.eth.gas_price
            
            txn = pi_contract.functions.submitRunResult(
                run_id,
                "",
                b'\x00' * 32,
                2
            ).build_transaction({
                'from': variables.OWNER_ADDRESS,
                'nonce': nonce,
                'gas': 800_000,
                'gasPrice': gas_price,
            })
            
            signed_txn = w3.eth.account.sign_transaction(txn, private_key=variables.OWNER_PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"Run {run_id} failed. TX hash: {tx_hash.hex()}")
            
    except Exception as e:
        print(f"Error processing AI task {run_id}: {str(e)}")