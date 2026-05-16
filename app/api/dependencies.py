from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

# In a true production environment, this would be loaded from your .env file
VALID_API_KEYS = {
    "nexus-admin-999",
    "nexus-user-123"
}

# Instructs FastAPI to look for an "X-API-Key" header in incoming requests
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Dependency to validate the API key for protected routes."""
    if api_key in VALID_API_KEYS:
        return api_key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing X-API-Key header",
    )