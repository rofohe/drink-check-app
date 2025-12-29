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

    drive_service.permissions().create(
        fileId=file["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()

    return f"https://drive.google.com/uc?id={file['id']}"

# --------------------------------------------------
# OCR helpers
# --------------------------------------------------
def ocr_best_rotation(image: Image.Image, lang: str) -> str:
    """
    Try OCR at multiple rotations and keep the most informative result
    """
    best_text = ""
    best_len = 0

    for angle in [0, 90, 180, 270]:
        rotated = image.rotate(angle, expand=True)
        text =
