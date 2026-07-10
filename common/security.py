from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from common.config import conf
from common.logger import my_logger

bearer_scheme = HTTPBearer(auto_error=False)


def verify_admin_token(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin token")
    if credentials.credentials != conf.ADMIN_TOKEN:
        my_logger.warning("Invalid admin token attempt")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
