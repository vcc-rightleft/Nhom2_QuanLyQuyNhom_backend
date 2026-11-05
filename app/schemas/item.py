from typing import Optional
from pydantic import BaseModel

class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: int

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None

class ItemResponse(ItemBase):
    id: int

    class Config:
        from_attributes = True