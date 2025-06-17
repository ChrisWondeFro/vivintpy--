from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str | None = None # API's own refresh token

class TokenData(BaseModel):
    username: str | None = None
    vivint_refresh_token: str | None = None # Added for storing Vivint refresh token
