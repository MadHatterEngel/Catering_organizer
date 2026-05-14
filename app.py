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
        background-image: linear-gradient(rgba(255, 255, 255, 0.70), rgba(255, 255, 255, 0.70)), 
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

    }}
    [data-testid="stMarkdownContainer"] p {{ font-family: 'Helvetica Neue', Helvetica, sans-serif; color: #222222; font-weight: 600; }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)
except Exception as e:
    pass 

# =========================================================
# --- SETUP API ---
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

# =========================================================
# --- APP UI ---
# =========================================================
st.set_page_config(page_title="Madhatter Catering Prep", page_icon="📋")
st.title("📋 Kitchen Prep List Generator")
st.write("Upload a catering PDF to generate a calculated, table-formatted prep list!")

uploaded_file = st.file_uploader("Upload your receipt (PDF)", type="pdf")

if uploaded_file is not None:
    st.success("File uploaded successfully! Processing...")
    
    with st.spinner("Analyzing PDF layout and calculating totals..."):
        
        # We NO LONGER extract text manually! 
        # We pass the raw PDF file directly to Gemini's vision engine.
        pdf_bytes = uploaded_file.getvalue()
        document_part = types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf')
        
        prompt = """
        You are an expert kitchen expeditor. I have attached a catering order receipt as a PDF. Read the document carefully.
        Your task is to calculate all totals and generate a "Catering Order Prep & Kitchen List" using the STRICT HTML TABLE structure provided below.
        
        CRITICAL RULES:
        1. Read the layout visually. Connect sides, dressings, and temperatures to the correct items.
        2. DO THE MATH: Aggregate every single identical item. If there are 15 Medium-Rare Sirloins, output the total 15. Do not list items one by one.
        3. Extract the Order Number, Client/Platform (e.g., Zifty Dispatch), Date, Time, and Headcount for the header. If the Date or Time says "Incomplete", write "Not Specified".
        4. Group sub-items (like meat temps, salad dressings, or "NO butter" notes) underneath their parent item using the nested <ul> lists from the template.
        5. Output ONLY the raw HTML code. Do not wrap in ```html markdown blocks.

        USE EXACTLY THIS HTML STRUCTURE AND CSS:
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            *, *::before, *::after { box-sizing: border-box; }
            @page { size: letter; margin: 20mm; background-color: #ffffff; }
            body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; font-size: 11pt; line-height: 1.4; }
            h1 { text-align: center; font-size: 18pt; margin-bottom: 5px; }
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
            <p class="subtitle">Order #[ORDER_NUM] | [CLIENT_NAME] | [DATE] @ [TIME] | Headcount: [HEADCOUNT]</p>

            <h2>Non-Food Items & Packaging</h2>
            <table>
                <thead><tr><th class="col-done">Done</th><th>Item</th><th>Qty</th></tr></thead>
                <tbody>
                    <tr><td class="done-cell"><div class="checkbox"></div></td><td><strong>Tableware (Napkins, Plates, Utensils)</strong></td><td class="qty">45</td></tr>
                </tbody>
            </table>

            <h2>Proteins</h2>
            <table>
                <thead><tr><th class="col-done">Done</th><th>Item & Details</th><th>Qty</th></tr></thead>
                <tbody>
                    <tr>
                        <td class="done-cell"><div class="checkbox"></div></td>
                        <td>
                            <strong>Center-Cut Sirloin (6 oz)</strong>
                            <ul class="sub-category">
                                <li>Rare: 1</li>
                                <li>Medium-Rare: 15</li>
                            </ul>
                        </td>
                        <td class="qty">16</td>
                    </tr>
                </tbody>
            </table>

            <h2>Sides</h2>
            <table>
                <thead><tr><th class="col-done">Done</th><th>Item & Details</th><th>Qty</th></tr></thead>
                <tbody>
                    <tr>
                        <td class="done-cell"><div class="checkbox"></div></td>
                        <td>
                            <strong>Loaded Baked Potato</strong>
                            <div class="special-note">* 1 of these needs Butter, Cheese, and Bacon bits added</div>
                        </td>
                        <td class="qty">4</td>
                    </tr>
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

   
        
        # Pass both the raw PDF part and the prompt text to the model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[document_part, prompt],
        )
        html_content = response.text.replace("```html", "").replace("```", "").strip()

    with st.spinner("Generating beautiful PDF..."):
        # 4. Convert the AI-generated HTML into a downloadable PDF
        output_pdf = "kitchen_prep_list.pdf"
        HTML(string=html_content).write_pdf(output_pdf)
    
    st.success("Done! Your kitchen prep list is ready.")
    
    # 5. Provide the download button
    with open(output_pdf, "rb") as pdf_file:
        st.download_button(
            label="⬇️ Download Kitchen Prep PDF",
            data=pdf_file,
            file_name="kitchen_prep_list.pdf",
            mime="application/pdf"
        )
        
    os.remove(output_pdf)
    with st.spinner("Reading PDF and extracting summary data..."):
        # 1. Read the uploaded PDF
        reader = PdfReader(uploaded_file)
        raw_text = ""
        for page in reader.pages:
            raw_text += page.extract_text() + "\n"
                        # 2. Ask the AI to format the raw text into our specific SUMMARY HTML layout
        prompt = f"""
        You are an expert catering expeditor. I am giving you the raw text extracted from a catering order PDF. 
        Your task is to create a high-level "Catering Order Expeditor Summary" WITHOUT individual names, but WITH exact calculated quantities.
        
        CRITICAL EXTRACTION RULES FOR PDF TEXT:
        1. HEADER DATA: Search the text for 'Headcount', 'Date', 'Time'. (Note: If the text literally says "Incomplete Date" or "Not specified", output exactly that).
        2. COUNTING PROTEINS: Identify every single protein order. Pay close attention to sizes (e.g., 'Large', 'Small'). You MUST treat 'Large' and 'Small' as TWO COMPLETELY SEPARATE CATEGORIES. Do not merge them. Count EXACTLY how many of each exist.
        3. COUNTING SIDES: For EACH protein group, look at the sides listed beneath it. You MUST do the math. If 'House Salad' appears 3 times under the Large Chicken, you must add them up and output "[ 3x ] House Salad". Do not just write [1x] for everything.
        4. ORDERS WITH A 'QTY': If there is a 'qty' or 'quantity' listed, this should be taken into account. 
        
        Format the output EXACTLY as a beautiful, professional HTML document using inline CSS. Follow this exact structure:
        
        1. Document Title: Prominently display "Catering Order Expeditor Summary" at the top.
        2. Header Banner: Display the extracted Order Number, Date, Time, and Headcount. 
        3. "Special Instructions" Section: List any general order instructions, tableware notes.
        4. "Meal Breakdown" Section: 
            - Group the list by Protein AND Size.
            - INCLUDE the exact calculated total quantity for the protein in the heading (e.g., "<h2>[ 2x ] Perfectly Grilled Salmon (Large)</h2>").
            - Under each protein, add a subheading called "Associated Sides:".
            - List the sides and dressings that go with that protein, AND INCLUDE THEIR CALCULATED TOTAL QUANTITIES. 
            - Format the sides with a functional expeditor checkbox: "<li><span style='border: 1px solid #333; padding: 0 5px;'>&nbsp;&nbsp;</span> <strong>[ 3x ]</strong> House Salad w/ Ranch</li>"
        5. "Desserts" Section: Aggregate and list all desserts with their TOTAL CALCULATED QUANTITIES.
        6. "Meat Temperatures" Section: Aggregate and list all requested meat temperatures with their TOTAL CALCULATED QUANTITIES.
        
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
