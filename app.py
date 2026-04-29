import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from pyzbar.pyzbar import decode
from PIL import Image
import subprocess
import time

# Backend ko background mein start karne ke liye
@st.cache_resource
def start_backend():
    subprocess.Popen(["uvicorn", "main:app", "--port", "8000"])
    time.sleep(2) # Backend ko start hone ka waqt dena

start_backend()

API_URL = "http://127.0.0.1:8000"

# --- DECODER & PDF ---
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

# --- SESSION ---
if 'logged_in' not in st.session_state: 
    st.session_state.logged_in = False
    st.session_state.cart = []

if not st.session_state.logged_in:
    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        res = requests.post(f"{API_URL}/login", params={"username":u, "password":p})
        if res.status_code == 200:
            st.session_state.logged_in, st.session_state.user, st.session_state.role = True, res.json()['username'], res.json()['role']
            st.rerun()
else:
    st.sidebar.title(f"👤 {st.session_state.user}")
    menu = ["Billing", "Inventory", "Reports", "Staff Management"] if st.session_state.role == "admin" else ["Billing"]
    choice = st.sidebar.selectbox("Menu", menu)

    # --- BILLING (Scanner Integrated) ---
    if choice == "Billing":
        st.header("🧾 POS Terminal")
        cam_on = st.checkbox("Turn on Billing Scanner")
        scanned_b = ""
        if cam_on:
            pic = st.camera_input("Scan Product")
            if pic: scanned_b = scan_barcode(Image.open(pic))

        products = requests.get(f"{API_URL}/products").json()
        p_map = {p['barcode']: p for p in products}
        name_map = {p['name']: p for p in products}
        
        default_idx = 0
        if scanned_b in p_map:
            default_idx = list(name_map.keys()).index(p_map[scanned_b]['name'])
            st.success(f"Found: {p_map[scanned_b]['name']}")

        sel_name = st.selectbox("Product", list(name_map.keys()), index=default_idx)
        qty = st.number_input("Quantity", min_value=1, value=1)
        if st.button("Add to Cart"):
            p = name_map[sel_name]
            st.session_state.cart.append({"product_id":p['id'], "name":sel_name, "quantity":qty, "price":p['price'], "staff_name":st.session_state.user})
            st.rerun()

        if st.session_state.cart:
            st.table(st.session_state.cart)
            if st.button("Finalize Sale"):
                res = requests.post(f"{API_URL}/generate-bill", json=st.session_state.cart)
                pdf_bytes = create_pdf(st.session_state.cart, res.json()['total'])
                st.download_button("Download Invoice", pdf_bytes, "invoice.pdf")
                st.session_state.cart = []

    # --- INVENTORY (Scanner Integrated) ---
    elif choice == "Inventory":
        st.header("📦 Manage Stock")
        cam_on_inv = st.checkbox("Scan Barcode for Stock")
        inv_scanned = ""
        if cam_on_inv:
            pic_inv = st.camera_input("Inventory Scan")
            if pic_inv: inv_scanned = scan_barcode(Image.open(pic_inv))

        with st.form("inv"):
            n, b, p, q = st.text_input("Name"), st.text_input("Barcode", value=inv_scanned), st.number_input("Price"), st.number_input("Qty")
            if st.form_submit_button("Save"):
                requests.post(f"{API_URL}/add-product", params={"name":n, "price":p, "qty":q, "barcode":b})
                st.success("Updated")
        st.dataframe(requests.get(f"{API_URL}/products").json())

    # --- REPORTS & STAFF ---
    elif choice == "Reports":
        data = requests.get(f"{API_URL}/sales-report").json()
        st.plotly_chart(px.bar(pd.DataFrame(data), x="timestamp", y="total_price"))

    elif choice == "Staff Management":
        with st.form("staff"):
            nu, np = st.text_input("Username"), st.text_input("Password")
            if st.form_submit_button("Create Account"):
                requests.post(f"{API_URL}/create-user", json={"username":nu, "password":np, "role":"staff"})
                st.success("Staff Created")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()