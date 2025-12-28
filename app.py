# --------------------------------------------------
# label_app.py
# --------------------------------------------------

import streamlit as st
from datetime import datetime
from PIL import Image
import pytesseract
from langdetect import detect, LangDetectException
import gspread
from google.oauth2.service_account import Credentials

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="Bottle Label Logger",
    page_icon="🍾",
    layout="centered"
)

st.title("🍾 Bottle Label Logger")

# --------------------------------------------------
# Google Sheets helper
# --------------------------------------------------
def get_worksheet():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1JHcRPvNsl7og23GT-0AKNmoyD8BwFPP0UB_myJsvBcg"
    return client.open_by_url(SHEET_URL).worksheet("label_db")

# --------------------------------------------------
# Image upload (optional OCR)
# --------------------------------------------------
uploaded_image = st.file_uploader(
    "Upload a photo of the bottle label (optional)",
    type=["jpg", "jpeg", "png"]
)

ocr_text = ""
language = ""

if uploaded_image:
    image = Image.open(uploaded_image)
    st.image(image, caption="Uploaded label", use_container_width=True)

    with st.spinner("Extracting text (best effort)…"):
        ocr_text = pytesseract.image_to_string(image)

    st.subheader("OCR result (for reference only)")
    st.text_area("Extracted text", ocr_text, height=120)

    try:
        language = detect(ocr_text)
    except LangDetectException:
        language = "unknown"

    st.write(f"Detected language: `{language}`")

# --------------------------------------------------
# Core product info (manual)
# --------------------------------------------------
st.subheader("Product information")

brand = st.text_input("Brand name")
sortiment = st.text_input("Sortiment (e.g. Pils, IPA, Lager, Radler)")
alcohol_percent = st.number_input(
    "Alcohol %",
    min_value=0.0,
    max_value=20.0,
    step=0.1
)

# --------------------------------------------------
# Ingredients
# --------------------------------------------------
st.subheader("Ingredients")

col1, col2, col3 = st.columns(3)
with col1:
    ing_brauwasser = st.checkbox("Brauwasser")
with col2:
    ing_hops = st.checkbox("Hopfen")
with col3:
    ing_gerstenmalz = st.checkbox("Gerstenmalz")

# --------------------------------------------------
# Calories
# --------------------------------------------------
st.subheader("Calories (per 100 ml)")

col1, col2 = st.columns(2)
with col1:
    cal_kj = st.number_input("kJ", min_value=0, step=1)
with col2:
    cal_kcal = st.number_input("kcal", min_value=0, step=1)

# --------------------------------------------------
# Price & location
# --------------------------------------------------
st.subheader("Purchase info")

price = st.number_input("Price", min_value=0.0, step=0.1)
location = st.text_input("Location (shop, bar, city, country)")

# --------------------------------------------------
# Experience
# --------------------------------------------------
tried = st.checkbox("I have tried this product")

quality = None
preference = None

if tried:
    st.subheader("Your experience")

    quality = st.slider(
        "Quality",
        min_value=1,
        max_value=7,
        value=4
    )

    preference = st.slider(
        "Preference",
        min_value=1,
        max_value=7,
        value=4
    )

# --------------------------------------------------
# Save
# --------------------------------------------------
if st.button("Save to database"):
    if not brand:
        st.error("Brand name is required.")
    else:
        try:
            ws = get_worksheet()
            ws.append_row([
                datetime.now().isoformat(),
                language,
                brand,
                sortiment,
                alcohol_percent,
                ing_brauwasser,
                ing_hops,
                ing_gerstenmalz,
                cal_kj,
                cal_kcal,
                price,
                location,
                tried,
                quality if tried else "",
                preference if tried else "",
                ocr_text
            ])
            st.success("Saved to Google Sheets ✅")
        except Exception as e:
            st.error(f"Failed to save: {e}")
