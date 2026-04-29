# 🛒 Smart Store Management System

A professional, full-stack Retail POS (Point of Sale) and Inventory Management System designed for small business efficiency. Built with **Streamlit** and **PostgreSQL (Neon DB)**.

## ✨ Key Features

- **🔐 Secure Access**: Integrated login for Admin (**Aditya Kashyap**) and Staff members.
- **🧾 Smart POS Terminal**: 
  - Real-time billing with a built-in barcode scanner (Mobile Camera).
  - [cite_start]**Stock Validation**: Automatically prevents sales if stock is insufficient. [cite: 1]
  - [cite_start]Instant price & total amount popups with celebration balloons. [cite: 1]
- **📦 Inventory Control**: 
  - [cite_start]Add/Update products with compact UI columns. [cite: 1]
  - [cite_start]Real-time stock tracking with 1-based indexing for better readability. [cite: 1]
- [cite_start]**👥 Staff Management**: Admins can manage team accounts with Full Names and Usernames. [cite: 1]
- [cite_start]**📊 Sales Analytics**: Visual revenue tracking using Plotly bar charts. [cite: 1]

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **Database**: PostgreSQL (Neon.tech Cloud)
- **ORM**: SQLAlchemy
- **PDF Generation**: FPDF
- **Scanning**: PyZbar & OpenCV

## 🚀 Installation & Setup

    1. **Clone the Repository**:
    git clone [https://github.com/YOUR_USERNAME/Store-Manager-Pro.git](https://github.com/YOUR_USERNAME/Store-Manager-Pro.git)
    cd Store-Manager-Pro


    2. **Install Dependencies**:
    pip install -r requirements.txt

    Database Configuration:
    Add neon DB link in streamlit secrets or in .streamlit/secrets.toml.


    Run Locally:
    streamlit run app.py
