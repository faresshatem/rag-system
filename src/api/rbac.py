from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredential
import jwt
from typing import List

security = HTTPBearer()

SECRET_KEY = "super_secret_key_change_in_production"
ALGORITHM = "HS256"

ALL_DOMAINS = ["HR", "IT", "Finance"]

def get_current_user_domains(credentials: HTTPAuthorizationCredential = Depends(security)) -> List[str]:
    """
    Task 3 & 4 combined security function.
    Intercepts the token, reads user identity/roles, and calculates domain bounds.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")
        allowed_domains_str = payload.get("allowed_domains", "")
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid security token or signature failed authentication."
        )
    if role == "Admin":
        return ALL_DOMAINS
    elif role in ["HR", "IT"]:
        user_domains = [d.strip() for d in allowed_domains_str.split(",") if d.strip()]
        final_domains = [d for d in user_domains if d == role]
        return final_domains
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Your assigned role does not belong to an approved domain namespace."
        )
