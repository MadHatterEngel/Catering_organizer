import streamlit as st
from google import genai
from PyPDF2 import PdfReader
from weasyprint import HTML
import os
import base64
from dotenv import load_dotenv

# =========================================================
# --- CUSTOM APP STYLING (THE FADED LOGO BACKGROUND) ---
# =========================================================

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    # Try finding the file safely
    img_path = '8696.png'
    if not os.path.exists(img_path):
        img_path = os.path.join(os.path.dirname(__file__), '8696.png')
        
    bin_str = get_base64_of_bin_file(img_path)
    
    # Injected CSS targeting the absolute top layer (.stApp)
    page_bg_img = f'''
    <style>
    /* Forces the background image to cover the entire screen */
    .stApp {{
        background-image: linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)), 
                          url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* Makes the top header bar transparent so it doesn't cut off the image */
    header[data-testid="stHeader"] {{
        background-color: transparent !important;
    }}
    
    /* Clean up headers to pop against the background */
    h1 {{ color: #111111; font-weight: 800; text-shadow: 1px 1px 2px rgba(255,255,255,0.5); }}
    
    /* Madhatter Orange Upload Button */
    [data-testid="stFileUploader"] {{
        background-color: rgba(246, 185, 59, 0.95);
        color: white;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        border: 2px solid #e1a028;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    
    /* Customize text info above upload */
    [data-testid="stMarkdownContainer"] p {{
        font-family: 'Helvetica Neue', Helvetica, sans-serif;
        color: #222222;
        font-weight: 600;
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)
except Exception as e:
    pass # Silently proceed if the image isn't found

# =========================================================
# --- REST OF APP LOGIC (API Setup, PDF Processing) ---
# =========================================================

# --- SETUP API ---
# Load environment variables from .env file (local development)
load_dotenv()

# Get API key from Streamlit secrets (deployment) or environment variables (local)
try:
    api_key = st.secrets.get("GEMINI_API_KEY")
except Exception:
    api_key = None

if not api_key:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ GEMINI_API_KEY not found. Please set it in your environment or Streamlit secrets.")
    st.stop()

# Initialize the new SDK Client
client = genai.Client(api_key=api_key)

# --- APP UI ---
st.set_page_config(page_title="Madhatter Catering Prep", page_icon="📋")
st.title("📋 Catering Order Prep Summary")
st.write("Upload a catering PDF to generate a clean, aggregated prep summary without individual names!")

uploaded_file = st.file_uploader("Upload your receipt (PDF)", type="pdf")

if uploaded_file is not None:
    st.success("File uploaded successfully! Processing...")
    
    with st.spinner("Reading PDF and extracting summary data..."):
        # 1. Read the uploaded PDF
        reader = PdfReader(uploaded_file)
        raw_text = ""
        for page in reader.pages:
            raw_text += page.extract_text() + "\n"
        
        # 2. Ask the AI to format the raw text into our specific SUMMARY HTML layout
        prompt = f"""
        You are a catering expeditor assistant. I am giving you the raw text from a catering order receipt.
        Your task is to create a high-level "Catering Order Expeditor Summary" WITHOUT individual names.
        
        CRITICAL EXTRACTION RULES:
        - The raw text is extracted from a PDF. Because of this, variables like 'HEADCOUNT', the Date, the Time, 'Side', 'Dessert', 'Please Prepare Meat', and 'Special Instructions' will often appear on the lines directly UNDERNEATH their respective labels, rather than next to them. 
        - You must carefully read the lines below headings to associate the correct values. 
        
        Format the output EXACTLY as a beautiful, professional HTML document using inline CSS. Follow this exact structure:
        
        1. Document Title: Prominently display "Catering Order Expeditor Summary" at the top.
        2. Header Banner: Display the extracted Order Number, Date, Time, and Headcount (e.g., "<p>Order #12345 | Thursday, May 14 @ 5:25 PM | Headcount: 45</p>").
        3. "Special Instructions" Section: List any general order instructions, tableware notes, or global setup details.
        4. "Meal Breakdown" Section: 
            - Group the list by Protein.
            - IMPORTANT: If the receipt specifies a size for the protein/meal (e.g., "6 oz", "Large") or indicates it is a "Boxed Meal", INCLUDE that size and bundle information directly in the Protein Group Heading.
            - Under each protein, add a subheading called "Associated Sides:".
            - List the aggregate sides and dressings that go with that protein. 
            - DO NOT INCLUDE ANY NAMES. Just add an empty checkbox "[ ]" next to the side groupings so the kitchen can check them off.
        5. "Desserts" Section: Aggregate and list all desserts requested in the order.
        6. "Meat Temperatures" Section: Aggregate and list all requested meat temperatures (e.g., "15x Medium-Rare, 8x Medium").
        
        - ONLY output the raw HTML code, nothing else. No markdown formatting blocks.
        
        Raw Catering Receipt Text:
        {raw_text}
        """
        
        # 3. Call the AI using the 2.5 model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        html_content = response.text.replace("```html", "").replace("```", "").strip()

    with st.spinner("Generating beautiful PDF..."):
        # 4. Convert the AI-generated HTML into a downloadable PDF
        output_pdf = "catering_prep_summary.pdf"
        HTML(string=html_content).write_pdf(output_pdf)
    
    st.success("Done! Your summary list is ready.")
    
    # 5. Provide the download button
    with open(output_pdf, "rb") as pdf_file:
        st.download_button(
            label="⬇️ Download Prep Summary PDF",
            data=pdf_file,
            file_name="catering_prep_summary.pdf",
            mime="application/pdf"
        )
        
    # Clean up the file
    os.remove(output_pdf)
