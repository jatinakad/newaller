import structlog
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()
security = HTTPBearer(auto_error=False)

_jwks_cache: dict | None = None


async def _get_keycloak_public_key() -> dict:
    """Fetch JWKS from Keycloak for token verification."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    if settings.KEYCLOAK_PUBLIC_KEY:
        _jwks_cache = {"direct_key": settings.KEYCLOAK_PUBLIC_KEY}
        return _jwks_cache

    try:
        jwks_url = (
            f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
            f"/protocol/openid-connect/certs"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url, timeout=10)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            return _jwks_cache
    except Exception as e:
        logger.warning("keycloak_jwks_fetch_failed", error=str(e))
        return {}


async def verify_token(request: Request) -> dict:
    """
    Verify JWT token from Authorization header.
    In development mode, allows unauthenticated requests with default doctor identity.
    """
    if settings.APP_ENV == "development":
        # In dev mode, allow requests without auth but check if token is provided
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {
                "sub": request.headers.get("X-Doctor-Id", "dev-doctor-001"),
                "preferred_username": "dev-doctor",
                "realm_access": {"roles": ["DOCTOR"]},
            }

    credentials: HTTPAuthorizationCredentials | None = await security(request)
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    token = credentials.credentials

    try:
        jwks = await _get_keycloak_public_key()

        if "direct_key" in jwks:
            payload = jwt.decode(
                token,
                jwks["direct_key"],
                algorithms=["RS256"],
                audience=settings.KEYCLOAK_CLIENT_ID,
            )
        elif "keys" in jwks:
            header = jwt.get_unverified_header(token)
            key = next((k for k in jwks["keys"] if k["kid"] == header.get("kid")), None)
            if not key:
                raise HTTPException(status_code=401, detail="Invalid token signing key")
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=settings.KEYCLOAK_CLIENT_ID,
            )
        else:
            # Fallback: decode without verification in dev
            if settings.APP_ENV == "development":
                payload = jwt.get_unverified_claims(token)
            else:
                raise HTTPException(status_code=401, detail="Cannot verify token")

        return payload

    except JWTError as e:
        logger.warning("jwt_verification_failed", error=str(e))
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def require_role(required_role: str):
    """Dependency that checks if the authenticated user has a specific role."""
    async def _check_role(request: Request):
        user = await verify_token(request)
        roles = user.get("realm_access", {}).get("roles", [])
        if required_role not in roles and settings.APP_ENV != "development":
            raise HTTPException(status_code=403, detail=f"Role '{required_role}' required")
        return user
    return _check_role