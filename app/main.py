from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import BackgroundTasks
from pydantic import BaseModel
from eth_account.messages import defunct_hash_message
from eth_account.messages import encode_defunct
from fastapi import UploadFile, File, Form

from web3 import Web3
from eth_account import Account
import secrets
import hashlib
import uuid
import variables

from app.auth import create_jwt, decode_jwt
from app.ai_models.run_ai import process_ai_task

from app.contracts import token_contract, pi_contract, w3, token_address, pi_address

CATALOG = [
    {"id": "chat_ds", "name": "Ask deepseek", "description": "Promt to deepseek to process", "price": 100},
    {"id": "yolo8_dt", "name": "Yolo8 detection", "description": "Detect basic classes on image using YOLO", "price": 500},
]

RUNS = {}

app = FastAPI()

nonces = {}  # In-memory nonce store
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")
app.mount("/downloads", StaticFiles(directory="app/downloads"), name="downloads")

class AddressRequest(BaseModel):
    address: str

class SignatureRequest(BaseModel):
    address: str
    signature: str

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    balance_wei = w3.eth.get_balance(token_address)
    balance_eth = w3.from_wei(balance_wei, 'ether')
    print("Contract ETH balance:", balance_eth, "ETH")

    return templates.TemplateResponse("index.html", {"request": request, "contract_address": token_address, "pi_contract_address": pi_address})

@app.post("/get_nonce")
def get_nonce(data: AddressRequest):
    nonce = secrets.token_hex(16)
    nonces[data.address.lower()] = nonce
    return {"nonce": nonce}

@app.get("/me")
def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ")[1]
    payload = decode_jwt(token)

    if payload is None or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {"address": payload["sub"]}

@app.get("/balance")
def get_balance(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ")[1]
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    address = payload["sub"]
    checksum_address = Web3.to_checksum_address(address)
    balance = token_contract.functions.balanceOf(checksum_address).call()

    return {"address": address, "PIT_balance": balance}

@app.get("/runs")
def get_user_runs(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ")[1]
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    address = payload["sub"]
    checksum_address = Web3.to_checksum_address(address)

    try:
        user_runs = pi_contract.functions.runsOf(checksum_address).call()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch runs: {e}")

    formatted_runs = [] 
    for run in user_runs:
        (
            requester,
            input_link,
            input_hash,
            output_link,
            output_hash,
            random_state,
            status_int,
        ) = run

        formatted_runs.append({
            "requester":       requester,
            "status":          int(status_int),           # enum → число (или конвертируйте в строку)
            "inputDataLink":   input_link,
            "inputDataHash":   Web3.to_hex(input_hash),
            "outputDataLink":  output_link,
            "outputDataHash":  Web3.to_hex(output_hash) if output_hash != b'\x00' * 32 else None,
            "randomState":     random_state,
        })

    return {"runs": formatted_runs}

@app.post("/verify_signature")
def verify_signature(data: SignatureRequest):
    address = data.address.lower()
    nonce = nonces.get(address)
    if not nonce:
        raise HTTPException(status_code=400, detail="Nonce not found")

    message = encode_defunct(text=nonce)

    try:
        recovered_address = Web3().eth.account.recover_message(message, signature=data.signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    if recovered_address.lower() != address:
        raise HTTPException(status_code=401, detail="Signature mismatch")

    token = create_jwt(address)
    address = recovered_address
    checksum_address = Web3.to_checksum_address(address)
    balance = token_contract.functions.balanceOf(checksum_address).call()

    print("Expected address:", address)
    print("Recovered address:", recovered_address)
    print("Nonce:", nonce)
    print("Signature:", data.signature)
    print("PIT Balance:", balance)

    return {"token": token, "address": recovered_address, "PIT_balance": balance}

@app.post("/buy_tokens")
async def buy_tokens(request: Request):
    data = await request.json()
    eth_amount = data.get("eth_amount")

    if not eth_amount or float(eth_amount) <= 0:
        raise HTTPException(status_code=400, detail="Invalid ETH amount")

    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    eth_value = w3.to_wei(eth_amount, 'ether')

    token = auth.split(" ")[1]
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    address = payload["sub"]
    checksum_address = Web3.to_checksum_address(address)

    nonce = w3.eth.get_transaction_count(checksum_address)

    # Either call buyTokens() explicitly, or send ETH directly to the contract
    tx = token_contract.functions.exchangeEthToTokens().build_transaction({
        'from': checksum_address,
        'value': eth_value,
        'nonce': nonce,
        'gas': 200_000,
        'gasPrice': w3.eth.gas_price,
    })

    signed_tx = w3.eth.account.sign_transaction(tx, variables.OWNER_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    balance_wei = w3.eth.get_balance(token_address)
    balance_eth = w3.fromWei(balance_wei, 'ether')
    print("Contract ETH balance:", balance_eth, "ETH")

    return {"tx_hash": tx_hash.hex()}

@app.get("/ai/catalog")
def ai_catalog():
    return CATALOG

@app.post("/ai/prepare_run")
async def prepare_run(
    request: Request,
    background_tasks: BackgroundTasks,
    job_id: str = Form(...),
    data: UploadFile = File(...)):
    user = _jwt_user(request)                      # same JWT helper
    contents = await data.read()
    input_hash = Web3.keccak(contents)
    random_state = uuid.uuid4().hex

    job = next((j for j in CATALOG if j["id"] == job_id), None)
    assert job is not None

    new_file_name = f"{random_state}_{data.filename}"

    cont_path = f"./app/uploads/{new_file_name}"
    with open(cont_path, "wb") as f:
        f.write(contents)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ")[1]
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    address = payload["sub"]
    checksum_address = Web3.to_checksum_address(address)

    nonce = w3.eth.get_transaction_count(variables.OWNER_ADDRESS)
    gas_price = w3.eth.gas_price

    bal = token_contract.functions.balanceOf(checksum_address).call()
    print("balance =", bal)

    # 2. Разрешение (allowance) пользователя на контракт
    allow = token_contract.functions.allowance(checksum_address, pi_contract.address).call()
    print("allowance =", allow)

    # 3. Цена запуска
    print("run price =", job["price"])

    txn = pi_contract.functions.requestRun(
        checksum_address, f"/uploads/{new_file_name}", input_hash, random_state, job["price"]
    ).build_transaction({
        'from': variables.OWNER_ADDRESS,
        'nonce': nonce,
        'gas': 800_000,
        'gasPrice': gas_price,
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key=variables.OWNER_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    logs = pi_contract.events.RunRequested().process_receipt(receipt)
    if not logs:
        print("RunRequested event not found")

    run_id = logs[0]["args"]["runId"]
    background_tasks.add_task(
        process_ai_task,
        run_id=run_id,
        job_id=job_id,
        input_path=new_file_name,
        requester=checksum_address,
        random_state=random_state
    )

def _jwt_user(request: Request) -> str:
    """Extract user address from JWT in Authorization header."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = auth.split(" ")[1]
    payload = decode_jwt(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    return Web3.to_checksum_address(payload["sub"])
