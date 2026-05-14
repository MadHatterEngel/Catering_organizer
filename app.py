import streamlit as st
from google import genai
from google.genai import types
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
    img_path = '8696.png'
    if not os.path.exists(img_path):
        img_path = os.path.join(os.path.dirname(__file__), '8696.png')
        
    bin_str = get_base64_of_bin_file(img_path)
    
    page_bg_img = f'''
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(255, 255, 255, 0.65), rgba(255, 255, 255, 0.65)), 
                          url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    header[data-testid="stHeader"] {{ background-color: transparent !important; }}
    h1 {{ color: #7851A9; font-weight: 800; text-shadow: 1px 1px 2px rgba(255,255,255,0.8); }}
    [data-testid="stMarkdownContainer"] p {{ font-family: 'Helvetica Neue', Helvetica, sans-serif; color: #444444; font-weight: 600; }}
    [data-testid="stFileUploader"] {{
        background-color: rgba(120, 81, 169, 0.95);
        color: white; padding: 15px; border-radius: 8px; font-weight: bold;
        border: 2px solid #5e3a8c; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    [data-testid="stFileUploader"] button {{
        color: #7851A9 !important; background-color: white !important; 
        border: 1px solid #5e3a8c !important; font-weight: bold;
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)
except Exception as e:
    pass

# =========================================================
# --- REST OF APP LOGIC (API Setup, PDF Processing) ---
# =========================================================

load_dotenv()

try:
    api_key = st.secrets.get("GEMINI_API_KEY")
except Exception:
    api_key = None

if not api_key:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ GEMINI_API_KEY not found. Please set it in your environment or Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- APP UI ---
st.set_page_config(page_title="Madhatter Catering Organizer", page_icon="🎩")
st.title("🎩Catering Order Organizer🎩")
st.write("📋Upload your catering PDF and I will Mad Hatter it right up into an organized list for you!")

uploaded_file = st.file_uploader("Upload your receipt (PDF)", type="pdf")

if uploaded_file is not None:
    st.success("File uploaded successfully! Processing...")
    
    with st.spinner("Analyzing PDF layout and calculating totals..."):
        
        pdf_bytes = uploaded_file.getvalue()
        document_part = types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf')

        prompt = """
        You are an expert kitchen expeditor. I have attached a catering order receipt as a PDF. Read the document carefully.
        Your task is to calculate all totals and generate a "Catering Order Prep & Kitchen List" using the STRICT HTML TABLE structure provided below.
        
        CRITICAL EXTRACTION RULES FOR PDF TEXT:
        1. HEADER DATA: Search the text visually for 'Headcount', 'Date', 'Time'. (Note: If the text literally says "Incomplete Date" or "Not specified", output exactly that).
        2. COUNTING PROTEINS: Identify every single protein order. Pay close attention to sizes (e.g., 'Large', 'Small'). You MUST treat 'Large' and 'Small' as TWO COMPLETELY SEPARATE CATEGORIES. Do not merge them. Count EXACTLY how many of each exist.
        3. COUNTING SIDES: For EACH protein group, look at the sides listed beneath it. You MUST do the math. If 'House Salad' appears 3 times under the Large Chicken, you must add them up and output "[ 3x ] House Salad". Do not just write [1x] for everything.
        4. ORDERS WITH A 'QTY': If there is a 'qty' or 'quantity' listed, this should be taken into account.
        5. Output ONLY the raw HTML code. Do not wrap in ```html markdown blocks.

        USE EXACTLY THIS HTML STRUCTURE AND CSS:
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            *, *::before, *::after { box-sizing: border-box; }
            @page { size: letter; margin: 20mm; background-color: #ffffff; }
            body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; font-size: 11pt; line-height: 1.4; }
            h1 { text-align: center; font-size: 18pt; margin-bottom: 5px; color: #7851A9; }
            p.subtitle { text-align: center; color: #666; margin-top: 0; margin-bottom: 20px; font-size: 11pt; }
            h2 { font-size: 14pt; color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 4px; margin-top: 20px; margin-bottom: 10px; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 15px; page-break-inside: avoid; }
            th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; vertical-align: middle; }
            th { background-color: #f4f6f7; font-weight: bold; color: #333; }
            th.col-done { width: 50px; text-align: center; }
            td.qty { text-align: center; font-weight: bold; width: 60px; font-size: 12pt; }
            td.done-cell { text-align: center; }
            .checkbox { display: inline-block; width: 18px; height: 18px; border: 2px solid #bdc3c7; border-radius: 3px; }
            ul.sub-category { margin: 6px 0 0 20px; padding: 0; list-style-type: circle; font-size: 10pt; color: #555; }
            ul.sub-category li { margin-bottom: 3px; }
            .special-note { color: #d35400; font-weight: bold; font-size: 9.5pt; margin-top: 4px; padding-left: 10px; border-left: 3px solid #f39c12; }
        </style>
        </head>
        <body>
            <h1>Catering Order Prep & Kitchen List</h1>
            <p class="subtitle">Order #[ORDER_NUM] | [DATE] @ [TIME] | Headcount: [HEADCOUNT]</p>

            <h2>Non-Food Items & Packaging</h2>
            <table>
                <thead><tr><th class="col-done">Done</th><th>Item</th><th>Qty</th></tr></thead>
                <tbody>
                    </tbody>
            </table>

            <h2>Proteins</h2>
            <table>
                <thead><tr><th class="col-done">Done</th><th>Item & Details</th><th>Qty</th></tr></thead>
                <tbody>
                    </tbody>
            </table>

            <h2>Sides</h2>
            <table>
                <thead><tr><th class="col-done">Done</th><th>Item & Details</th><th>Qty</th></tr></thead>
                <tbody>
                    </tbody>
            </table>

            <h2>Desserts</h2>
            <table>
                <thead><tr><th class="col-done">Done</th><th>Item</th><th>Qty</th></tr></thead>
                <tbody>
                    </tbody>
            </table>
        </body>
        </html>
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[document_part, prompt],
        )
        html_content = response.text.replace("```html", "").replace("```", "").strip()

    with st.spinner("Generating beautiful PDF..."):
        output_pdf = "kitchen_prep_list.pdf"
        HTML(string=html_content).write_pdf(output_pdf)
    
    st.success("Done! Your prep list is ready.")
    
    with open(output_pdf, "rb") as pdf_file:
        st.download_button(
            label="⬇️ Download Prep List PDF",
            data=pdf_file,
            file_name="kitchen_prep_list.pdf",
            mime="application/pdf"
        )
        
    os.remove(output_pdf)

