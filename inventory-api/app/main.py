import socket
import os
import requests
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.routes import inventory, replenishment
import jwt

app = FastAPI(title="Pharmacy Inventory Replenishment API")

# ─────────────────────────────────────────────
# Entra ID Configuration
# ─────────────────────────────────────────────
TENANT_ID = os.getenv("ENTRA_TENANT_ID")
CLIENT_ID = os.getenv("ENTRA_CLIENT_ID")

security  = HTTPBearer()

# ─────────────────────────────────────────────
# Validate JWT Token from External Entra ID
# Called on every protected API request
# ─────────────────────────────────────────────
def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    try:
        # Fetch Microsoft public keys
        jwks_url = (
            f"https://login.microsoftonline.com/"
            f"{TENANT_ID}/discovery/v2.0/keys"
        )
        jwks     = requests.get(jwks_url).json()

        # Get key ID from token header
        header   = jwt.get_unverified_header(token)
        kid      = header.get("kid")

        # Find matching public key
        rsa_key  = None
        for key in jwks.get("keys", []):
            if key["kid"] == kid:
                rsa_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Public key not found"
            )

        # Decode and validate the token
        payload = jwt.decode(
            token,
            key=rsa_key,
            algorithms=["RS256"],
            audience=CLIENT_ID
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired — please sign in again"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )

# ─────────────────────────────────────────────
# Mount static files and register routes
# All inventory and replenishment routes
# require a valid Entra ID token
# ─────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(
    inventory.router,
    dependencies=[Depends(verify_token)]
)
app.include_router(
    replenishment.router,
    dependencies=[Depends(verify_token)]
)

# ─────────────────────────────────────────────
# Public routes — no auth required
# ─────────────────────────────────────────────
@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")

@app.get("/health")
def health_check():
    return {
        "status":   "healthy",
        "service":  "inventory-api",
        "servedBy": socket.gethostname()
    }
