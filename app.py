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
    
    /* Upload Box Styling */
    [data-testid="stFileUploader"] {{
        background-color: rgba(120, 81, 169, 0.95);
        color: white; padding: 15px; border-radius: 8px; font-weight: bold;
        border: 2px solid #5e3a8c; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    [data-testid="stFileUploader"] button {{
        color: #7851A9 !important; background-color: white !important; 
        border: 1px solid #5e3a8c !important; font-weight: bold;
    }}
    
    /* Make checkboxes pop slightly */
    div[data-testid="stCheckbox"] label span {{ color: #222; font-weight: bold; }}
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
st.set_page_config(page_title="Madhatter Catering Organizer", page_icon="🎩", layout="centered")
st.title("🎩Catering Order Organizer🎩")
st.write("📋Upload your catering PDF and I will Mad Hatter it right up into an organized list for you!")

# Create a 2-column layout so the checkboxes sit to the right of the uploader
col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader("Upload your receipt (PDF)", type="pdf")

with col2:
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    st.write("### ⚙️ Output Format")
    # Summary is TRUE (checked) by default, Names is FALSE (unchecked) by default
    summary_check = st.checkbox("Summary List", value=True)
    names_check = st.checkbox("List with names", value=False)

# Common HTML Head/Style used for both PDFs
html_style = """
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
    .name-badge { font-weight: bold; color: #7851A9; font-size: 11pt; }
</style>
"""

if uploaded_file is not None:
    if not summary_check and not names_check:
        st.warning("⚠️ Please select at least one formatting option to the right of the upload button!")
    else:
        st.success("File uploaded successfully! Processing...")
        
        pdf_bytes = uploaded_file.getvalue()
        document_part = types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf')
        
        generated_files = []

        # ==========================================
        # 1. GENERATE SUMMARY LIST (If Checked)
        # ==========================================
        if summary_check:
            with st.spinner("Calculating math for Summary List..."):
                prompt_summary = f"""
                You are an expert kitchen expeditor. Read the attached catering order receipt carefully.
                Generate a "Catering Prep Summary List" focusing purely on calculated totals.
                
                CRITICAL RULES:
                1. DO THE MATH: Aggregate every single identical item. Treat different sizes (e.g., Large vs Small) as separate items.
                2. Extract Order Number, Client/Platform, Date, Time, and Headcount for the header. If missing, write "Not Specified".
                3. ONLY output raw HTML code. Do not include markdown blocks.
                
                USE EXACTLY THIS HTML STRUCTURE:
                <!DOCTYPE html><html><head>{html_style}</head><body>
                <h1>Catering Prep Summary List</h1>
                <p class="subtitle">Order #[ORDER_NUM] | [DATE] @ [TIME] | Headcount: [HEADCOUNT]</p>
                
                <h2>Non-Food Items & Packaging</h2>
                <table><thead><tr><th class="col-done">Done</th><th>Item</th><th>Qty</th></tr></thead><tbody></tbody></table>
                
                <h2>Proteins Summary</h2>
                <table><thead><tr><th class="col-done">Done</th><th>Item & Details</th><th>Qty</th></tr></thead><tbody></tbody></table>
                
                <h2>Sides Summary</h2>
                <table><thead><tr><th class="col-done">Done</th><th>Item & Details</th><th>Qty</th></tr></thead><tbody></tbody></table>
                
                <h2>Desserts Summary</h2>
                <table><thead><tr><th class="col-done">Done</th><th>Item</th><th>Qty</th></tr></thead><tbody></tbody></table>
                </body></html>
                """
                
                response_sum = client.models.generate_content(model='gemini-2.5-flash', contents=[document_part, prompt_summary])
                html_sum = response_sum.text.replace("```html", "").replace("```", "").strip()
                
                sum_filename = "Summary_List.pdf"
                HTML(string=html_sum).write_pdf(sum_filename)
                generated_files.append({"name": sum_filename, "label": "Summary PDF"})

        # ==========================================
        # 2. GENERATE NAMES LIST (If Checked)
        # ==========================================
        if names_check:
            with st.spinner("Extracting names for Individual Orders List..."):
                prompt_names = f"""
                You are an expert kitchen expeditor. Read the attached catering order receipt carefully.
                Generate an "Individual Orders List" focusing on matching specific sides and desserts to specific names.
                
                CRITICAL RULES:
                1. DO NOT AGGREGATE. List each person's meal individually. 
                2. Group and sort the list by Entree, then by Entree Temp (if applicable), then by Side.
                3. Include the Entree name, Temp, Sides, Dessert, and the Name of the person who ordered it.
                4. Extract Order Number, Client/Platform, Date, Time, and Headcount for the header. If missing, write "Not Specified".
                5. ONLY output raw HTML code. Do not include markdown blocks.
                
                USE EXACTLY THIS HTML STRUCTURE:
                <!DOCTYPE html><html><head>{html_style}</head><body>
                <h1>Individual Orders List</h1>
                <p class="subtitle">Order #[ORDER_NUM] | [DATE] @ [TIME] | Headcount: [HEADCOUNT]</p>
                
                <h2>Individual Orders (Grouped by Entree)</h2>
                <table>
                    <thead><tr><th class="col-done">Done</th><th>Entree & Details</th><th>Name</th></tr></thead>
                    <tbody>
                        <tr>
                            <td class="done-cell"><div class="checkbox"></div></td>
                            <td>
                                <strong>Center-Cut Sirloin (6 oz)</strong> - <em>Temp: Medium-Rare</em>
                                <ul class="sub-category">
                                    <li>Side: Loaded Baked Potato</li>
                                    <li>Dessert: Brownie</li>
                                </ul>
                            </td>
                            <td class="name-badge">Jane Doe</td>
                        </tr>
                    </tbody>
                </table>
                </body></html>
                """
                
                response_names = client.models.generate_content(model='gemini-2.5-flash', contents=[document_part, prompt_names])
                html_names = response_names.text.replace("```html", "").replace("```", "").strip()
                
                names_filename = "Individual_Orders_List.pdf"
                HTML(string=html_names).write_pdf(names_filename)
                generated_files.append({"name": names_filename, "label": "List w/ Names PDF"})

        # ==========================================
        # 3. DISPLAY DOWNLOAD BUTTONS
        # ==========================================
        st.success("Done! Your requested list(s) are ready.")
        
        # Display buttons side-by-side if there are multiple
        cols = st.columns(len(generated_files))
        for i, file_info in enumerate(generated_files):
            with cols[i]:
                with open(file_info["name"], "rb") as f:
                    pdf_data = f.read()
                st.download_button(
                    label=f"⬇️ Download {file_info['label']}",
                    data=pdf_data,
                    file_name=file_info["name"],
                    mime="application/pdf",
                    key=file_info["name"] # Unique key so Streamlit doesn't get confused
                )
                
        # Clean up files from the server after they are loaded into the buttons
        for file_info in generated_files:
            if os.path.exists(file_info["name"]):
                os.remove(file_info["name"])
