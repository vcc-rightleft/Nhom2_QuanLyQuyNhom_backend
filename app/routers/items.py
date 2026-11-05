from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse
from app.crud import item as crud_item

router = APIRouter()

@router.get("/items", response_model=List[ItemResponse])
def read_items(db: Session = Depends(get_db)):
    return crud_item.get_items(db)

@router.post("/items", response_model=ItemResponse)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    return crud_item.create_item(db=db, item=item)

@router.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item: ItemUpdate, db: Session = Depends(get_db)):
    updated = crud_item.update_item(db, item_id, item)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục này")
    return updated

@router.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    deleted = crud_item.delete_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục này")
    return {"message": "Đã xoá thành công"}