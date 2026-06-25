from fastapi import Header, HTTPException, status
import os

API_KEY = os.environ.get("AINIS_API_KEY", "")


async def verify_api_key(x_api_key: str = Header(default=None)):
    if not API_KEY:
        raise RuntimeError("AINIS_API_KEY not set in environment")
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return True
