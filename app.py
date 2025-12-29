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

    # Make public
    drive_service.permissions().create(
        fileId=file["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()

    return f"https://drive.google.com/uc?id={file['id']}"

# --------------------------------------------------
# OCR helpers
# --------------------------------------------------
def ocr_best_rotation(image: Image.Image, lang: str) -> str:
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
# Session state defaults
# --------------------------------------------------
if "uploaded_image_bytes" not in st.session_state:
    st.session_state.uploaded_image_bytes = None
if "ocr_text" not in st.session_state:
    st.session_state.ocr_text = ""
if "saved_flag" not in st.session_state:
    st.session_state.saved_flag = False

# --------------------------------------------------
# Beverage type
# --------------------------------------------------
beverage = st.radio("Select beverage type", ["Beer", "Wine"])

# --------------------------------------------------
# Image upload
# --------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload label image (optional)",
    ["jpg", "jpeg", "png", "heic"]
)

if uploaded_file:
    st.session_state.uploaded_image_bytes = uploaded_file.read()

    if uploaded_file.name.lower().endswith(".heic"):
        heif_file = pillow_heif.read_heif(io.BytesIO(st.session_state.uploaded_image_bytes))
        image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
    else:
        image = Image.open(io.BytesIO(st.session_state.uploaded_image_bytes))

    image = ImageOps.exif_transpose(image)
    st.image(image, use_container_width=True)

    if st.checkbox("Run OCR (best effort)"):
        with st.spinner("Running OCR (trying rotations)…"):
            st.session_state.ocr_text = ocr_best_rotation(image, lang="eng")
        st.text_area("OCR result", st.session_state.ocr_text, height=150)

# --------------------------------------------------
# Label info
# --------------------------------------------------
brand = st.text_input("Brand")
sortiment = st.text_input("Sortiment / Style")
description = st.text_area("Describe the beverage")
alcohol_percent = st.number_input("Alcohol %", 0.0, 25.0, step=0.1)

country = st.text_input("Country")
postal_code = st.text_input("Postal code")
language_choice = st.selectbox("Label language", ["English", "German", "French", "Spanish"])

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
beer_color = ""
beer_bitterness = ""
beer_vals = wine_vals = ("", "", "", "")

if beverage == "Beer":
    beer_color = st.selectbox("Beer color", ["pale", "gold", "orange", "brown", "black"])
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
# Save & Clear
# --------------------------------------------------
def save_to_sheet():
    if not brand:
        st.error("Brand is required")
        return

    try:
        sheet, drive = get_clients()

        image_url = ""
        if st.session_state.uploaded_image_bytes:
            if uploaded_file.name.lower().endswith(".heic"):
                heif_file = pillow_heif.read_heif(io.BytesIO(st.session_state.uploaded_image_bytes))
                image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
            else:
                image = Image.open(io.BytesIO(st.session_state.uploaded_image_bytes))
            image = ImageOps.exif_transpose(image)
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
        st.session_state.saved_flag = True

    except Exception as e:
        st.error(f"Save failed: {e}")

def clear_form():
    st.session_state.uploaded_image_bytes = None
    st.session_state.ocr_text = ""
    st.session_state.saved_flag = False
    st.experimental_rerun()

st.button("Save to database", on_click=save_to_sheet)

if st.session_state.saved_flag:
    st.button("Clear form for next entry", on_click=clear_form)
