from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    next_agent: str
    target_domain: Optional[str] = None
    step_count: int
    answer: Optional[str] = None

class IngestRequest(BaseModel):
    domain: str
    content: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "User"
    allowed_domains: str = ""

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    allowed_domains: str
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
