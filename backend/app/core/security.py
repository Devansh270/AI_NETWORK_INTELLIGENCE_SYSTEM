from fastapi import Header, HTTPException, status
from dotenv import load_dotenv
from pathlib import Path
import os

# Load infra/.env
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / "infra" / ".env")

API_KEY = os.getenv("AINIS_API_KEY", "")


async def verify_api_key(x_api_key: str = Header(default=None)):
    if not API_KEY:
        raise RuntimeError("AINIS_API_KEY not set in environment")

    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    return True