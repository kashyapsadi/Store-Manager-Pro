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
    full_name = Column(String) # Naya field staff ke naam ke liye

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

def get_db():
    db = SessionLocal()
    try: return db
    finally: db.close()

# --- UI UTILS ---
def scan_barcode(image):
    decoded = decode(image)
    for obj in decoded: return obj.data.decode("utf-8")
    return None

st.set_page_config(page_title="Store Pro Live", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.cart = []

db = get_db()

if not st.session_state.logged_in:
    # LOGIN SCREEN (Size chota kiya gaya hai)
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.title("🔐 Login")
        u_in = st.text_input("Username")
        p_in = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            user = db.query(User).filter(User.username == u_in, User.password == p_in).first()
            if user:
                st.session_state.logged_in, st.session_state.user, st.session_state.role = True, user.username, user.role
                st.rerun()
            else: st.error("Invalid Credentials!")
else:
    # --- SIDEBAR FIX ---
    st.sidebar.title(f"👤 {st.session_state.user}")
    
    # "Aditya Kashyap" sirf admin ko dikhega
    if st.session_state.role == "admin":
        st.sidebar.markdown("### **Aditya Kashyap**")
    
    menu = ["Billing", "Inventory", "Reports", "Staff Management"] if st.session_state.role == "admin" else ["Billing"]
    choice = st.sidebar.selectbox("Menu", menu)

    # 1. BILLING (Size chota kiya gaya hai)
    if choice == "Billing":
        st.header("🧾 POS Terminal")
        
        # Scanner section ko thoda compact kiya
        cam_on = st.checkbox("Enable Scanner")
        scanned_b = ""
        if cam_on:
            pic = st.camera_input("Scan", label_visibility="collapsed")
            if pic: scanned_b = scan_barcode(Image.open(pic))

        # Inputs ko columns mein dala taaki bars choti ho jayein
        col1, col2 = st.columns([2, 1])
        
        prods = db.query(Product).all()
        name_map = {p.name: p for p in prods}
        p_map = {p.barcode: p for p in prods}
        
        default_idx = 0
        if scanned_b in p_map:
            default_idx = list(name_map.keys()).index(p_map[scanned_b].name)

        with col1:
            sel_name = st.selectbox("Select Product", list(name_map.keys()), index=default_idx)
        with col2:
            qty = st.number_input("Qty", min_value=1, value=1)
        
        if st.button("Add to Cart 🛒", use_container_width=False):
            p = name_map[sel_name]
            st.session_state.cart.append({"id": p.id, "name":sel_name, "quantity":qty, "price":p.price})
            st.toast("Added!")

        if st.session_state.cart:
            st.divider()
            st.subheader("Current Order")
            st.dataframe(pd.DataFrame(st.session_state.cart)[['name', 'quantity', 'price']], use_container_width=True)
            if st.button("Complete Transaction"):
                # (Wahi purana checkout logic...)
                st.success("Sale Recorded!")
                st.session_state.cart = []

    # 4. STAFF MANAGEMENT (Updated with Full Name)
    elif choice == "Staff Management":
        st.header("👥 Staff Management")
        
        # Account Creation Form
        with st.expander("➕ Create New Staff Account"):
            with st.form("staff_reg"):
                f_name = st.text_input("Staff Full Name (Aditya jaisa)")
                u_name = st.text_input("Username (Login ke liye)")
                p_word = st.text_input("Password", type="password")
                if st.form_submit_button("Create Account"):
                    db.add(User(username=u_name, password=p_word, role="staff", full_name=f_name))
                    db.commit()
                    st.success(f"Account created for {f_name}")

        # Staff List View
        st.subheader("Active Staff Members")
        all_staff = db.query(User).filter(User.role == "staff").all()
        if all_staff:
            staff_list = [{"Username": s.username, "Full Name": s.full_name} for s in all_staff]
            st.table(staff_list)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
