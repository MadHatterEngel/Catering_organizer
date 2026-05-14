import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from weasyprint import HTML
import os
from dotenv import load_dotenv

# --- SETUP API ---
# Load environment variables from .env file (local development)
load_dotenv()

# Get API key from Streamlit secrets (deployment) or environment variables (local)
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ GEMINI_API_KEY not found. Please set it in your environment or Streamlit secrets.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- APP UI ---
st.set_page_config(page_title="Catering Organizer", page_icon="🍱")
st.title("🍱 Catering Order Organizer")
st.write("Upload an EZCater or generic catering PDF, and this app will magically organize it into a scannable expeditor checklist!")

uploaded_file = st.file_uploader("Upload your receipt (PDF)", type="pdf")

if uploaded_file is not None:
    st.success("File uploaded successfully! Processing...")
    
    with st.spinner("Reading PDF and extracting orders..."):
        # 1. Read the uploaded PDF
        reader = PdfReader(uploaded_file)
        raw_text = ""
        for page in reader.pages:
            raw_text += page.extract_text() + "\n"
        
        # 2. Ask the AI to format the raw text into our specific HTML layout
        prompt = f"""
        You are a catering expeditor assistant. I am giving you the raw text from a catering order receipt.
        Extract all names, proteins, meat temperatures, sides, special instructions, and desserts.
        
        Format the output EXACTLY as a beautiful, professional HTML document using inline CSS. 
        - Group the list by Protein.
        - Under each protein, group by Side item.
        - Under the sides, list the names alphabetically.
        - Put expeditor checkboxes [ ] next to the names.
        - Color code the desserts (e.g., green for cookies, purple for brownies).
        - ONLY output the raw HTML code, nothing else. No markdown formatting blocks.
        
        Raw Catering Receipt Text:
        {raw_text}
        """
        
        # Call the AI
        response = model.generate_content(prompt)
        html_content = response.text.replace("```html", "").replace("```", "").strip()

    with st.spinner("Generating beautiful PDF..."):
        # 3. Convert the AI-generated HTML into a downloadable PDF
        output_pdf = "organized_catering_list.pdf"
        HTML(string=html_content).write_pdf(output_pdf)
    
    st.success("Done! Your organized list is ready.")
    
    # 4. Provide the download button
    with open(output_pdf, "rb") as pdf_file:
        st.download_button(
            label="⬇️ Download Organized PDF",
            data=pdf_file,
            file_name="organized_catering_list.pdf",
            mime="application/pdf"
        )
        
    # Optional: Clean up the file after it's loaded into the button
    os.remove(output_pdf)
