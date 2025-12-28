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
    return client.open_by_url(SHEET_URL).worksheet("drink")

# --------------------------------------------------
# Image upload
# --------------------------------------------------
uploaded_image = st.file_uploader(
    "Upload a photo of the bottle label",
    type=["jpg", "jpeg", "png"]
)

ocr_text = ""
language = ""

if uploaded_image:
    image = Image.open(uploaded_image)
    st.image(image, caption="Uploaded label", use_container_width=True)

    # OCR
    with st.spinner("Extracting text..."):
        ocr_text = pytesseract.image_to_string(image)

    st.subheader("Extracted text")
    st.text_area("OCR Result", ocr_text, height=150)

    # Language detection
    try:
        language = detect(ocr_text)
    except LangDetectException:
        language = "unknown"

    st.write(f"**Detected language:** `{language}`")

# --------------------------------------------------
# Brand input
# --------------------------------------------------
brand = st.text_input("Brand name (confirm or edit)")

# --------------------------------------------------
# Tried it?
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
        value=4,
        help="1 = very poor, 7 = excellent"
    )

    preference = st.slider(
        "Preference",
        min_value=1,
        max_value=7,
        value=4,
        help="1 = dislike, 7 = love it"
    )

# --------------------------------------------------
# Save
# --------------------------------------------------
if st.button("Save to database"):
    if not uploaded_image:
        st.error("Please upload a label image first.")
    elif not brand:
        st.error("Please enter a brand name.")
    else:
        try:
            worksheet = get_worksheet()

            worksheet.append_row([
                datetime.now().isoformat(),
                language,
                brand,
                ocr_text,
                tried,
                quality if tried else "",
                preference if tried else ""
            ])

            st.success("Saved to Google Sheets ✅")
        except Exception as e:
            st.error(f"Failed to save: {e}")


# In[ ]:




