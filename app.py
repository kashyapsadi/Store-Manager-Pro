import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from pyzbar.pyzbar import decode
from PIL import Image
import cv2
import numpy as np
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

def get_db():
    db = SessionLocal()
    try: return db
    finally: db.close()

# --- SMART SCANNER LOGIC (Grayscale for Mobile Accuracy) ---
def smart_scan(image):
    try:
        # Convert PIL image to OpenCV format 
        img_array = np.array(image.convert('RGB'))
        # Convert to grayscale to improve barcode detection 
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        
        # Try scanning the processed grayscale image first 
        decoded = decode(gray)
        if not decoded:
            # Fallback to original image if grayscale fails 
            decoded = decode(image)
            
        for obj in decoded: 
            return obj.data.decode("utf-8")
    except:
        pass
    return None

def create_pdf(cart, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "KREATOR KNOT - STORE INVOICE", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for item in cart:
        pdf.cell(200, 10, f"{item['name']} x {item['quantity']} = Rs.{item['price']*item['quantity']}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, f"TOTAL AMOUNT: Rs.{total}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- UI CONFIG ---
st.set_page_config(page_title="Store Pro Live", layout="wide")

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
                st.session_state.logged_in = True
                st.session_state.user = user.username
                st.session_state.role = user.role
                st.session_state.f_name = user.full_name
                st.rerun()
            else: st.error("Invalid Credentials!")
else:
    # --- SIDEBAR BRANDING  ---
    st.sidebar.title(f"👤 {st.session_state.f_name if st.session_state.role == 'admin' else st.session_state.user}")
    menu = ["Billing", "Inventory", "Reports", "Staff Management"] if st.session_state.role == "admin" else ["Billing"]
    choice = st.sidebar.selectbox("Navigate Menu", menu)

    # 1. BILLING SECTION (With Stock Validation )
    if choice == "Billing":
        st.header("🧾 POS Terminal")
        
        c_cam, _ = st.columns([1, 3])
        cam_on = c_cam.checkbox("Scan Product Barcode")
        
        scanned_b = ""
        if cam_on:
            pic = st.camera_input("Focus on Barcode & Click Take Photo", label_visibility="visible")
            if pic:
                scanned_b = smart_scan(Image.open(pic))
                if not scanned_b:
                    st.warning("⚠️ Barcode detect nahi hua. Focus karke firse try karein.")
                else:
                    st.success(f"✅ Scanned: {scanned_b}")

        prods = db.query(Product).all()
        name_map = {p.name: p for p in prods}
        p_map = {p.barcode: p for p in prods}
        
        default_idx = 0
        if scanned_b in p_map:
            default_idx = list(name_map.keys()).index(p_map[scanned_b].name)

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            sel_name = st.selectbox("Product", list(name_map.keys()), index=default_idx)
        with col2:
            qty = st.number_input("Quantity", min_value=1, value=1)
        with col3:
            st.write("##")
            if st.button("Add to Cart 🛒", use_container_width=True):
                p = name_map[sel_name]
                # Stock check logic 
                if qty > p.stock_quantity:
                    st.error(f"❌ Check stock! Only {p.stock_quantity} quantity available.")
                else:
                    st.session_state.cart.append({"id": p.id, "name":sel_name, "quantity":qty, "price":p.price})
                    st.toast(f"{sel_name} added!")
                    st.rerun()

        if st.session_state.cart:
            st.divider()
            st.subheader("🛒 Current Cart")
            df_cart = pd.DataFrame(st.session_state.cart)[['name', 'quantity', 'price']]
            df_cart.index = df_cart.index + 1 # 1-based indexing 
            st.table(df_cart)
            
            btn_col1, btn_col2 = st.columns(2)
            if btn_col1.button("Clear Cart 🗑️", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
            if btn_col2.button("Generate Bill & Print 🖨️", use_container_width=True):
                total_amt = 0
                for item in st.session_state.cart:
                    p = db.query(Product).filter(Product.id == item['id']).first()
                    p.stock_quantity -= item['quantity']
                    total_amt += (item['price'] * item['quantity'])
                    db.add(Sale(product_name=item['name'], quantity=item['quantity'], total_price=item['price']*item['quantity'], staff_name=st.session_state.user))
                db.commit()
                st.balloons()
                st.success(f"### ✅ Transaction Complete!")
                st.metric(label="Total Amount", value=f"Rs. {total_amt}")
                st.download_button("📥 Download Invoice PDF", create_pdf(st.session_state.cart, total_amt), "invoice.pdf", "application/pdf")
                st.session_state.cart = []

    # 2. INVENTORY SECTION (With Auto-Update )
    elif choice == "Inventory":
        st.header("📦 Inventory Management")
        inv_cam = st.checkbox("Scan Barcode for Stock Update")
        inv_b = ""
        if inv_cam:
            inv_pic = st.camera_input("Focus on Barcode & Click Take Photo")
            if inv_pic:
                inv_b = smart_scan(Image.open(inv_pic))
                if inv_b:
                    st.success(f"✅ Barcode Detected: {inv_b}")
                else:
                    st.warning("⚠️ Detect nahi hua, focus sahi karein.")

        with st.form("inv_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Item Name")
            barcode = c2.text_input("Barcode", value=inv_b)
            price = c1.number_input("Unit Price", min_value=0.0)
            stock = c2.number_input("Add Quantity", min_value=0)
            if st.form_submit_button("Save Product"):
                exist = db.query(Product).filter(Product.barcode == barcode).first()
                if exist:
                    exist.stock_quantity += stock
                    exist.price = price
                else:
                    db.add(Product(name=name, barcode=barcode, price=price, stock_quantity=stock))
                db.commit()
                st.success("Database Updated Successfully!")
        
        st.divider()
        st.subheader("Current Stock Status")
        stock_data = db.query(Product).all()
        if stock_data:
            df_stock = pd.DataFrame([{"Name": p.name, "Barcode": p.barcode, "Stock": p.stock_quantity, "Price": p.price} for p in stock_data])
            df_stock.index = df_stock.index + 1
            st.dataframe(df_stock, use_container_width=True)

    # 4. STAFF MANAGEMENT (Aditya's Team )
    elif choice == "Staff Management":
        st.header("👥 Staff Management")
        with st.form("staff_reg"):
            c1, c2 = st.columns(2)
            f_name = c1.text_input("Staff Full Name")
            u_name = c2.text_input("Username")
            p_word = c1.text_input("Password", type="password")
            if st.form_submit_button("Create Staff Account"):
                db.add(User(username=u_name, password=p_word, role="staff", full_name=f_name))
                db.commit()
                st.success(f"Success! Account for {f_name} created.")
        
        st.divider()
        staff_data = db.query(User).filter(User.role == "staff").all()
        if staff_data:
            df_staff = pd.DataFrame([{"Full Name": s.full_name, "Username": s.username} for s in staff_data])
            df_staff.index = df_staff.index + 1
            st.table(df_staff)

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
