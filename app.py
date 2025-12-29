# --------------------------------------------------
# label_app.py
# --------------------------------------------------

import streamlit as st
from datetime import datetime
from PIL import Image, ImageOps
import pillow_heif
import pytesseract
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="Beverage Label Logger",
    page_icon="🍾",
    layout="centered"
)

st.title("🍾 Beverage Label Logger")

# --------------------------------------------------
# Session state init
# --------------------------------------------------
if "ocr_text" not in st.session_state:
    st.session_state.ocr_text = ""

if "decoded_image_bytes" not in st.session_state:
    st.session_state.decoded_image_bytes = None

# --------------------------------------------------
# Reset helper
# --------------------------------------------------
def reset_form():
    st.session_state.clear()
    st.rerun()

# --------------------------------------------------
# Google helpers
# --------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://w
