# --------------------------------------------------
# label_app.py
# --------------------------------------------------

import streamlit as st
from datetime import datetime
from PIL import Image
from PIL import Image, ImageOps
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
# Google helpers
# --------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_clients():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    gs = gspread.authorize(creds)
    drive = build("drive", "v3", credentials=creds)
    sheet = gs.open_by_url(
        "https://docs.google.com/spreadsheets/d/1JHcRPvNsl7og23GT-0AKNmoyD8BwFPP0UB_myJsvBcg"
    ).worksheet("drink")
    return sheet, drive

def upload_image_to_drive(image, drive_service):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)

    file_metadata = {
        "name": f"label_{datetime.now().isoformat()}.png",
        "mimeType": "image/png"
    }

    media = MediaIoBaseUpload(buf, mimetype="image/png")
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    # Make public
    drive_service.permissions().create(
        fileId=file["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()

    return f"https://drive.google.com/uc?id={file['id']}"

# --------------------------------------------------
# OCR helpers
# --------------------------------------------------
def ocr_best_rotation(image, lang):
    """
    Try OCR at multiple rotations and keep the most informative result
    """
    best_text = ""
    best_len = 0

    for angle in [0, 90, 180, 270]:
        rotated = image.rotate(angle, expand=True)
        text = pytesseract.image_to_string(rotated, lang=lang)
        clean_len = len(text.strip())

        if clean_len > best_len:
            best_len = clean_len
            best_text = text

    return best_text

# --------------------------------------------------
# Beverage type
# --------------------------------------------------
beverage = st.radio("Select beverage type", ["Beer", "Wine"])

# --------------------------------------------------
# Image upload + OCR language choice
# --------------------------------------------------
uploaded_image = st.file_uploader("Upload label image (optional)", ["jpg", "jpeg", "png"])

language_map = {
    "English": "eng",
    "German": "deu",
    "French": "fra",
    "Spanish": "spa"
}

country = st.text_input("Country")
language_choice = st.selectbox("Label language", list(language_map.keys()))

ocr_text = ""

if uploaded_image:
    image = Image.open(uploaded_image)
    image = ImageOps.exif_transpose(image)  # 🔑 fix orientation
    st.image(image, use_container_width=True)

    if st.checkbox("Run OCR (best effort)"):
        with st.spinner("Running OCR…"):
            ocr_text = pytesseract.image_to_string(
                image,
        with st.spinner("Running OCR (trying rotations)…"):
            ocr_text = ocr_best_rotation(
                image=image,
                lang=language_map[language_choice]
            )
        st.text_area("OCR result", ocr_text, height=120)
        st.text_area("OCR result", ocr_text, height=150)

# --------------------------------------------------
# Core info
# --------------------------------------------------
brand = st.text_input("Brand")
sortiment = st.text_input("Sortiment / Style")
description = st.text_area("Describe the beverage")

alcohol_percent = st.number_input("Alcohol %", 0.0, 25.0, step=0.1)

# --------------------------------------------------
# Ingredients
# --------------------------------------------------
st.subheader("Ingredients")

col1, col2, col3 = st.columns(3)
with col1:
    ing_water = st.checkbox("Brauwasser")
with col2:
    ing_hops = st.checkbox("Hopfen")
with col3:
    ing_malt = st.checkbox("Gerstenmalz")

ing_other = st.text_input("Other ingredients")

# --------------------------------------------------
# Calories
# --------------------------------------------------
st.subheader("Calories (per 100 ml)")
cal_kj = st.number_input("kJ", min_value=0)
cal_kcal = st.number_input("kcal", min_value=0)

# --------------------------------------------------
# Purchase info
# --------------------------------------------------
price = st.number_input("Price", min_value=0.0, step=0.1)
location = st.text_input("Purchase location")

# --------------------------------------------------
# Ratings
# --------------------------------------------------
st.subheader("Ratings")

beer_vals = wine_vals = ("", "", "", "")

if beverage == "Beer":
    beer_vals = (
        st.slider("Taste quality", 1, 7, 4),
        st.slider("Aftertaste", 1, 7, 4),
        st.slider("Carbonation quality", 1, 7, 4),
        st.slider("Overall", 1, 7, 4)
    )

if beverage == "Wine":
    wine_vals = (
        st.slider("Taste quality", 1, 7, 4),
        st.slider("Dry ↔ Sweet", 1, 7, 4),
        st.slider("Aftertaste", 1, 7, 4),
        st.slider("Overall", 1, 7, 4)
    )

# --------------------------------------------------
# Save
# --------------------------------------------------
if st.button("Save to database"):
    if not brand:
        st.error("Brand is required")
    else:
        try:
            sheet, drive = get_clients()

            image_url = ""
            if uploaded_image:
                image_url = upload_image_to_drive(image, drive)

            sheet.append_row([
                datetime.now().isoformat(),
                beverage,
                brand,
                sortiment,
                country,
                language_choice,
                description,
                alcohol_percent,
                ing_water,
                ing_hops,
                ing_malt,
                ing_other,
                cal_kj,
                cal_kcal,
                price,
                location,
                *beer_vals,
                *wine_vals,
                image_url,
                ocr_text
            ])

            st.success("Saved successfully ✅")
        except Exception as e:
            st.error(f"Save failed: {e}")
