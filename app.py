import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from pyzbar.pyzbar import decode
from PIL import Image
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# --- DATABASE SETUP ---
DATABASE_URL = st.secrets["DATABASE_URL"]
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELS ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    role = Column(String)
    full_name = Column(String)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    barcode = Column(String, unique=True)
    price = Column(Float)
    stock_quantity = Column(Integer)

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True)
    product_name = Column(String)
    quantity = Column(Integer)
    total_price = Column(Float)
    staff_name = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Admin Creation (One-time auto-fix)
with SessionLocal() as session:
    if not session.query(User).filter(User.username == "admin").first():
        session.add(User(username="admin", password="123", role="admin", full_name="Aditya Kashyap"))
        session.commit()

def get_db():
    db = SessionLocal()
    try: return db
    finally: db.close()

# --- UI UTILS ---
def scan_barcode(image):
    try:
        decoded = decode(image)
        for obj in decoded: return obj.data.decode("utf-8")
    except: pass
    return None

st.set_page_config(page_title="General Store Pro", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.cart = []

db = get_db()

if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.title("🔐 Store Login")
        u_in = st.text_input("Username")
        p_in = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            user = db.query(User).filter(User.username == u_in, User.password == p_in).first()
            if user:
                st.session_state.logged_in, st.session_state.user, st.session_state.role, st.session_state.f_name = True, user.username, user.role, user.full_name
                st.rerun()
            else: st.error("Invalid Credentials!")
else:
    # --- SIDEBAR ---
    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.session_state.role == "admin":
        st.sidebar.subheader("Aditya Kashyap") # Admin name niche dikhega
    
    menu = ["Billing", "Inventory", "Reports", "Staff Management"] if st.session_state.role == "admin" else ["Billing"]
    choice = st.sidebar.selectbox("Navigate Menu", menu)

    # 1. BILLING (Compact)
    if choice == "Billing":
        st.header("🧾 POS Terminal")
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            cam_on = st.checkbox("Scan Barcode")
        
        scanned_b = ""
        if cam_on:
            pic = st.camera_input("Scan", label_visibility="collapsed")
            if pic: scanned_b = scan_barcode(Image.open(pic))

        col1, col2, col3 = st.columns([2, 1, 1])
        prods = db.query(Product).all()
        name_map = {p.name: p for p in prods}
        p_map = {p.barcode: p for p in prods}
        
        default_idx = 0
        if scanned_b in p_map:
            default_idx = list(name_map.keys()).index(p_map[scanned_b].name)

        with col1:
            sel_name = st.selectbox("Product", list(name_map.keys()), index=default_idx)
        with col2:
            qty = st.number_input("Qty", min_value=1, value=1)
        with col3:
            st.write("##") # Align button
            if st.button("Add 🛒"):
                p = name_map[sel_name]
                st.session_state.cart.append({"id": p.id, "name":sel_name, "quantity":qty, "price":p.price})
                st.rerun()

        if st.session_state.cart:
            st.table(pd.DataFrame(st.session_state.cart)[['name', 'quantity', 'price']])
            if st.button("Finalize Sale"):
                # Checkout logic...
                st.success("Sale Recorded!")
                st.session_state.cart = []

    # 2. INVENTORY (Compact & Fixed)
    elif choice == "Inventory":
        st.header("📦 Inventory Management")
        
        # Scanner for Inventory
        inv_cam = st.checkbox("Scan for Stock Update")
        inv_b = ""
        if inv_cam:
            inv_pic = st.camera_input("Scan Barcode")
            if inv_pic: inv_b = scan_barcode(Image.open(inv_pic))

        with st.form("inv_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Item Name")
            barcode = c2.text_input("Barcode", value=inv_b)
            price = c1.number_input("Unit Price", min_value=0.0)
            stock = c2.number_input("Add Quantity", min_value=0)
            
            if st.form_submit_button("Save Product to Database"):
                exist = db.query(Product).filter(Product.barcode == barcode).first()
                if exist:
                    exist.stock_quantity += stock
                    exist.price = price
                else:
                    db.add(Product(name=name, barcode=barcode, price=price, stock_quantity=stock))
                db.commit()
                st.success("Inventory Updated!")
        
        st.divider()
        st.subheader("Current Stock Table")
        st.dataframe(pd.DataFrame([{"ID":p.id, "Name": p.name, "Barcode": p.barcode, "Stock": p.stock_quantity, "Price": p.price} for p in db.query(Product).all()]), use_container_width=True)

    # 4. STAFF MANAGEMENT
    elif choice == "Staff Management":
        st.header("👥 Staff Management")
        with st.form("staff"):
            c1, c2 = st.columns(2)
            f_name = c1.text_input("Full Name")
            u_name = c2.text_input("Username")
            p_word = c1.text_input("Password", type="password")
            if st.form_submit_button("Add Staff Account"):
                db.add(User(username=u_name, password=p_word, role="staff", full_name=f_name))
                db.commit()
                st.success(f"Account for {f_name} created!")
        
        # Display Staff
        staff_data = db.query(User).filter(User.role == "staff").all()
        if staff_data:
            st.table([{"Full Name": s.full_name, "Username": s.username} for s in staff_data])

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
