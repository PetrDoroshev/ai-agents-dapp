from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from eth_account.messages import defunct_hash_message
from eth_account.messages import encode_defunct
from fastapi import UploadFile, File, Form

from web3 import Web3
from eth_account import Account
import secrets
import hashlib
import uuid

from app.auth import create_jwt, decode_jwt

from app.contracts import token_contract, pi_contract, w3, token_address, pi_address

CATALOG = [
    {"id": "style", "name": "Style‑Transfer", "description": "Apply Van‑Gogh style", "price": 500},
    {"id": "detect", "name": "Object‑Detect", "description": "YOLOv8",             "price": 100},
]

RUNS = {}

app = FastAPI()

nonces = {}  # In-memory nonce store
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")

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

    return templates.TemplateResponse("index.html", {"request": request, "contract_address": token_address})

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
        print("User_runs", user_runs)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch runs: {e}")

    # Optional: Format AIRun structs nicely
    formatted = [
        {
            "id": r[0],
            "score": r[1],
            "started": r[2]
        }
        for r in user_runs
    ]

    return {"runs": formatted}

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

@app.post("/run")
def start_run(request: Request, body: dict):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    payload = decode_jwt(auth.split()[1])
    if not payload:
        raise HTTPException(401, "Invalid token")

    user = Web3.to_checksum_address(payload["sub"])
    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(400, "Prompt required")

    new_run = {
        "id": 123,
        "score": 95,
        "started": int(time.time())
    }

    return new_run

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

    signed_tx = w3.eth.account.sign_transaction(tx, "0x8c9985ba187a4087774f1f6eb2fc9776070babf0194316cbdbc8d4e4f8f3dd62")
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
    job_id: str = Form(...),
    data: UploadFile = File(...)
):
    user = _jwt_user(request)                      # same JWT helper
    contents = await data.read()
    input_hash = Web3.keccak(contents)
    random_state = uuid.uuid4().hex

    path = f"./app/uploads/{random_state}_{data.filename}"
    with open(path, "wb") as f:
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

    nonce = w3.eth.get_transaction_count("0x0565a088f974D9B88C8DD09E268989744ba19aF2")
    gas_price = w3.eth.gas_price

    txn = pi_contract.functions.requestRun(
        checksum_address, f"/uploads/{path}", input_hash, random_state
    ).build_transaction({
        'from': "0x0565a088f974D9B88C8DD09E268989744ba19aF2",
        'nonce': nonce,
        'gas': 300_000,
        'gasPrice': gas_price,
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key="0x8c9985ba187a4087774f1f6eb2fc9776070babf0194316cbdbc8d4e4f8f3dd62")
    w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    return {
        "inputDataLink": f"/uploads/{random_state}_{data.filename}",
        "inputDataHash": input_hash.hex(),
        "randomState": random_state,
    }

@app.get("/create_run")
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

@app.post("/ai/pay_and_run")
async def ai_pay_and_run(request: Request, job_id: str, data: bytes):
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

    job = next((j for j in CATALOG if j["id"] == job_id), None)
    if not job: raise HTTPException(404, "job")
    _require_allowance(user, job["price"])

class ConfirmBody(BaseModel):
    job_id: str
    raw_tx: str

@app.post("/ai/confirm_run")
async def ai_confirm(request: Request, body: ConfirmBody):
    user = _jwt_user(request)
    txh = w3.eth.send_raw_transaction(body.raw_tx)
    w3.eth.wait_for_transaction_receipt(txh)

    # fake long task
    run_id = str(uuid.uuid4())
    RUNS[run_id] = {"status": "running"}
    asyncio.create_task(_simulate_run(run_id))
    return {"run_id": run_id}

async def _simulate_run(rid):
    await asyncio.sleep(10)
    RUNS[rid]["status"] = "done"

@app.get("/ai/status/{rid}")
def ai_status(rid: str):
    if rid not in RUNS: raise HTTPException(404)
    return RUNS[rid]

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