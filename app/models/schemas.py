from pydantic import BaseModel,Field
from typing import Optional


class Users(BaseModel):
    name: str = Field(max_length=100)
    username : str = Field(max_length=50)
    email : str = Field(max_length=255)
    phone : str  = Field(max_length=20)
    password_hash : str = Field(max_length=255)
    recovery_email : str = Field(max_length=255)
    role: str   = Field(max_length=20)
    send_invitation : Optional[bool] = False


class UserAuthentication(BaseModel):
    username: str =  Field(max_length=50)
    password: str

class UpdateUser(BaseModel):
    name : Optional[str] = None
    username : Optional[str] = None
    email : Optional[str] = None
    phone : Optional[str] = None
    password_hash : Optional[str] = None
    recovery_email : Optional[str] = None
    status : Optional[int] = None


class RecoveryPassword(BaseModel):
    email: str

class ResetPassword(BaseModel):
    token: str
    new_password: str


class Account(BaseModel):
    slug:str
    name: str
    api_key:str
    secret_key: str
    rfc: str
    address: str
    company_name:str
