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

# --- DATABASE SETUP (Direct) ---
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

# --- UTILS ---
def get_db():
    db = SessionLocal()
    try: return db
    finally: db.close()

def scan_barcode(image):
    decoded = decode(image)
    for obj in decoded: return obj.data.decode("utf-8")
    return None

def create_pdf(cart, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "STORE INVOICE", ln=True, align='C')
    pdf.ln(10)
    for item in cart:
        pdf.cell(200, 10, f"{item['name']} x {item['quantity']} = Rs.{item['price']*item['quantity']}", ln=True)
    pdf.cell(200, 10, f"TOTAL: Rs.{total}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- UI ---
st.set_page_config(page_title="Store Pro Live", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.cart = []

db = get_db()

if not st.session_state.logged_in:
    st.title("🔐 Store Login")
    u_in = st.text_input("Username")
    p_in = st.text_input("Password", type="password")
    if st.button("Login"):
        user = db.query(User).filter(User.username == u_in, User.password == p_in).first()
        if user:
            st.session_state.logged_in, st.session_state.user, st.session_state.role = True, user.username, user.role
            st.rerun()
        else: st.error("Galat credentials!")
else:
    st.sidebar.title(f"👤 {st.session_state.user}")
    menu = ["Billing", "Inventory", "Reports", "Staff Management"] if st.session_state.role == "admin" else ["Billing"]
    choice = st.sidebar.selectbox("Menu", menu)

    # BILLING
    if choice == "Billing":
        st.header("🧾 POS Terminal")
        cam_on = st.checkbox("Turn on Scanner")
        scanned_b = ""
        if cam_on:
            pic = st.camera_input("Scan Item")
            if pic: scanned_b = scan_barcode(Image.open(pic))

        prods = db.query(Product).all()
        p_map = {p.barcode: p for p in prods}
        name_map = {p.name: p for p in prods}
        
        default_idx = 0
        if scanned_b in p_map:
            default_idx = list(name_map.keys()).index(p_map[scanned_b].name)
            st.success(f"Found: {p_map[scanned_b].name}")

        sel_name = st.selectbox("Product", list(name_map.keys()), index=default_idx)
        qty = st.number_input("Quantity", min_value=1, value=1)
        if st.button("Add to Cart"):
            p = name_map[sel_name]
            st.session_state.cart.append({"id": p.id, "name":sel_name, "quantity":qty, "price":p.price})
            st.toast("Added!")

        if st.session_state.cart:
            st.table(st.session_state.cart)
            if st.button("Finalize Sale"):
                total = 0
                for item in st.session_state.cart:
                    p = db.query(Product).filter(Product.id == item['id']).first()
                    p.stock_quantity -= item['quantity']
                    total += (item['price'] * item['quantity'])
                    db.add(Sale(product_name=item['name'], quantity=item['quantity'], total_price=item['price']*item['quantity'], staff_name=st.session_state.user))
                db.commit()
                st.download_button("Download PDF", create_pdf(st.session_state.cart, total), "invoice.pdf")
                st.session_state.cart = []
                st.success("Sale Done!")

    # INVENTORY
    elif choice == "Inventory":
        st.header("📦 Manage Stock")
        with st.form("inv"):
            n, b, p, q = st.text_input("Name"), st.text_input("Barcode"), st.number_input("Price"), st.number_input("Qty")
            if st.form_submit_button("Save"):
                exist = db.query(Product).filter(Product.barcode == b).first()
                if exist:
                    exist.stock_quantity += q
                    exist.price = p
                else:
                    db.add(Product(name=n, barcode=b, price=p, stock_quantity=q))
                db.commit()
                st.success("Updated!")
        st.dataframe(pd.DataFrame([{"Name": p.name, "Stock": p.stock_quantity, "Price": p.price} for p in db.query(Product).all()]))

    # REPORTS
    elif choice == "Reports":
        sales = db.query(Sale).all()
        if sales:
            st.plotly_chart(px.bar(pd.DataFrame([{"Date": s.timestamp, "Total": s.total_price} for s in sales]), x="Date", y="Total"))

    # STAFF
    elif choice == "Staff Management":
        with st.form("staff"):
            nu, np = st.text_input("New User"), st.text_input("Pass")
            if st.form_submit_button("Create"):
                db.add(User(username=nu, password=np, role="staff"))
                db.commit()
                st.success("Staff Added")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
