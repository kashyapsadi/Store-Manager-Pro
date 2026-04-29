from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models, database
from pydantic import BaseModel
from typing import List

app = FastAPI()
models.Base.metadata.create_all(bind=database.engine)

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class CartItem(BaseModel):
    product_id: int
    quantity: int
    staff_name: str

@app.post("/create-user")
def create_user(user: UserCreate, db: Session = Depends(database.get_db)):
    db_user = models.User(username=user.username, password=user.password, role=user.role)
    db.add(db_user)
    db.commit()
    return {"message": "Success"}

@app.post("/login")
def login(username: str, password: str, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == username, models.User.password == password).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid Credentials")
    return {"username": user.username, "role": user.role}

@app.get("/products")
def get_products(db: Session = Depends(database.get_db)):
    return db.query(models.Product).all()

@app.post("/add-product")
def add_product(name: str, price: float, qty: int, barcode: str, db: Session = Depends(database.get_db)):
    existing = db.query(models.Product).filter(models.Product.barcode == barcode).first()
    if existing:
        existing.stock_quantity += qty
        existing.price = price
        db.commit()
        return {"message": "Stock Updated"}
    item = models.Product(name=name, price=price, stock_quantity=qty, barcode=barcode)
    db.add(item)
    db.commit()
    return {"message": "New Product Added"}

@app.post("/generate-bill")
def generate_bill(cart: List[CartItem], db: Session = Depends(database.get_db)):
    total = 0
    for item in cart:
        prod = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        prod.stock_quantity -= item.quantity
        subtotal = prod.price * item.quantity
        total += subtotal
        new_sale = models.Sale(product_name=prod.name, quantity=item.quantity, total_price=subtotal, staff_name=item.staff_name)
        db.add(new_sale)
    db.commit()
    return {"total": total}

@app.get("/sales-report")
def get_report(db: Session = Depends(database.get_db)):
    return db.query(models.Sale).all()

@app.get("/low-stock")
def low_stock(db: Session = Depends(database.get_db)):
    return db.query(models.Product).filter(models.Product.stock_quantity < 5).all()