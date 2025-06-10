from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from eth_account.messages import defunct_hash_message
from eth_account.messages import encode_defunct

from eth_account import Account
import secrets

from app.auth import create_jwt, decode_jwt

app = FastAPI()

nonces = {}  # In-memory nonce store
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

class AddressRequest(BaseModel):
    address: str

class SignatureRequest(BaseModel):
    address: str
    signature: str

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/get_nonce")
def get_nonce(data: AddressRequest):
    nonce = secrets.token_hex(16)
    nonces[data.address.lower()] = nonce
    return {"nonce": nonce}

@app.post("/verify_signature")
def verify_signature(data: SignatureRequest):
    address = data.address.lower()
    nonce = nonces.get(address)
    if not nonce:
        raise HTTPException(status_code=400, detail="Nonce not found")

    from web3 import Web3
    from eth_account.messages import encode_defunct

    message = encode_defunct(text=nonce)

    try:
        recovered_address = Web3().eth.account.recover_message(message, signature=data.signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    if recovered_address.lower() != address:
        raise HTTPException(status_code=401, detail="Signature mismatch")

    token = create_jwt(address)

    print("Expected address:", address)
    print("Recovered address:", recovered_address)
    print("Nonce:", nonce)
    print("Signature:", data.signature)

    return {"token": token, "address": recovered_address}