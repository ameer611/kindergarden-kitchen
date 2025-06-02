from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.schemas.ingredient import IngredientCreate, IngredientUpdate

class IngredientService:
    def get(self, db: Session, id: str) -> Optional[Ingredient]:
        return db.query(Ingredient).filter(Ingredient.id == id).first()

    def get_by_name(self, db: Session, *, name: str) -> Optional[Ingredient]:
        return db.query(Ingredient).filter(Ingredient.name == name).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, search: Optional[str] = None
    ) -> List[Ingredient]:
        query = db.query(Ingredient)
        if search:
            query = query.filter(Ingredient.name.ilike(f"%{search}%"))
        return query.offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: IngredientCreate) -> Ingredient:
        db_obj = Ingredient(
            name=obj_in.name,
            quantity_grams=obj_in.quantity_grams,
            delivery_date=obj_in.delivery_date,
            low_threshold_grams=obj_in.low_threshold_grams
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Ingredient, obj_in: IngredientUpdate
    ) -> Ingredient:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: str) -> Optional[Ingredient]:
        obj = db.query(Ingredient).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

ingredient_service = IngredientService()

