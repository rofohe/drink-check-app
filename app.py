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

if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = None

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
    image.save(buf, format="JPEG")
    buf.seek(0)

    file_metadata = {
        "name": f"label_{datetime.now().isoformat()}.jpg",
        "mimeType": "image/jpeg"
    }

    media = MediaIoBaseUpload(buf, mimetype="image/jpeg")
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    drive_service.permissions().create(
        fileId=file["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()

    return f"https://drive.google.com/uc?id={file['id']}"

# --------------------------------------------------
# Cached image decoding
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def decode_image(file_bytes: bytes, is_heic: bool) -> Image.Image:
    if is_heic:
        heif = pillow_heif.read_heif(file_bytes)
        img = Image.frombytes(
            heif.mode, heif.size, heif.data, "raw"
        )
    else:
        img = Image.open(io.BytesIO(file_bytes))

    return ImageOps.exif_transpose(img)

# --------------------------------------------------
# OCR helper (cached)
# --------------------------------------------------
@st.cache_data(show_spinner=True)
def ocr_best_rotation(image_bytes: bytes, lang: str) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    best_text = ""
    best_len = 0

    for angle in [0, 90, 180, 270]:
        rotated = image.rotate(angle, expand=True)
        text = pytesseract.image_to_string(rotated, lang=lang)
        if len(text.strip()) > best_len:
            best_text = text
            best_len = len(text.strip())

    return best_text

# --------------------------------------------------
# Beverage type
# --------------------------------------------------
beverage = st.radio("Select beverage type", ["Beer", "Wine"])

# --------------------------------------------------
# Image upload
# --------------------------------------------------
uploaded_image = st.file_uploader(
    "Upload label image (optional)",
    ["jpg", "jpeg", "png", "heic"]
)

language_map = {
    "English": "eng",
    "German": "deu",
    "French": "fra",
    "Spanish": "spa"
}

country = st.text_input("Country")
postal_code = st.text_input("Postal code")
language_choice = st.selectbox("Label language", list(language_map.keys()))

image = None

if uploaded_image:
    file_bytes = uploaded_image.read()
    is_heic = uploaded_image.name.lower().endswith(".heic")

    image = decode_image(file_bytes, is_heic)
    st.image(image, use_container_width=True)

    st.session_state.image_bytes = file_bytes

    if st.button("Run OCR (best effort)"):
        st.session_state.ocr_text = ocr_best_rotation(
            file_bytes,
            language_map[language_choice]
        )

if st.session_state.ocr_text:
    st.text_area("OCR result", st.session_state.ocr_text, height=150)

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

ing_water = st.checkbox("Brauwasser")
ing_hops = st.checkbox("Hopfen")
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

beer_color = ""
beer_bitterness = ""
beer_vals = wine_vals = ("", "", "", "")

if beverage == "Beer":
    beer_color = st.selectbox(
        "Beer color",
        ["pale", "gold", "orange", "brown", "black"]
    )
    beer_bitterness = st.slider("Sweet ↔ Bitter", 1, 7, 4)
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
            if image:
                image_url = upload_image_to_drive(image, drive)

            sheet.append_row([
                datetime.now().isoformat(),
                beverage,
                brand,
                sortiment,
                country,
                postal_code,
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
                beer_color,
                beer_bitterness,
                *beer_vals,
                *wine_vals,
                image_url,
                st.session_state.ocr_text
            ])

            st.success("Saved successfully ✅")
            st.button("Clear form", on_click=reset_form)

        except Exception as e:
            st.error(f"Save failed: {e}")
