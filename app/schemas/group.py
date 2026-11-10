from typing import Optional
from pydantic import BaseModel


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None


class JoinGroupRequest(BaseModel):
    invite_code: str


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    invite_code: str
    status: str

    class Config:
        from_attributes = True