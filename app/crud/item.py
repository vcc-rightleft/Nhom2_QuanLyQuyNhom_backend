from sqlalchemy.orm import Session
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate

def get_items(db: Session):
    return db.query(Item).all()

def get_item_by_id(db: Session, item_id: int):
    return db.query(Item).filter(Item.id == item_id).first()

def create_item(db: Session, item: ItemCreate):
    db_item = Item(name=item.name, description=item.description, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def update_item(db: Session, item_id: int, item_data: ItemUpdate):
    db_item = get_item_by_id(db, item_id)
    if not db_item:
        return None
    for field, val in item_data.model_dump(exclude_unset=True).items():
        setattr(db_item, field, val)
    db.commit()
    db.refresh(db_item)
    return db_item

def delete_item(db: Session, item_id: int):
    db_item = get_item_by_id(db, item_id)
    if not db_item:
        return None
    db.delete(db_item)
    db.commit()
    return db_item