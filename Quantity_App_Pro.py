import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import fitz
import io

# App Configuration
st.set_page_config(page_title="MIRZA-AUTO ESTIMATE AI", layout="wide")
st.markdown("### 🏗️ MIRZA-AUTO ESTIMATE AI: Professional Measurement System")

# Permanent Session State Initializations
if 'final_report' not in st.session_state:
    st.session_state.final_report = pd.DataFrame(columns=['Item No', 'Description', 'Nos', 'Length', 'Breath', 'Depth', 'Quantity', 'Unit', 'Rate', 'Total Quantity', 'Amount'])

if 'master_data' not in st.session_state:
    st.session_state.master_data = pd.DataFrame()

if 'canvas_key' not in st.session_state:
    st.session_state.canvas_key = 0
if 'last_item_no' not in st.session_state:
    st.session_state.last_item_no = ""
if 'last_description' not in st.session_state:
    st.session_state.last_description = ""

# --- Sidebar Controls ---
with st.sidebar:
    st.header("📂 Master Data Upload")
    master_file = st.file_uploader("Upload Item List (Excel)", type=['xlsx', 'xls'])
    if master_file:
        df_temp = pd.read_excel(master_file)
        df_temp.columns = df_temp.columns.str.strip().str.lower()
        st.session_state.master_data = df_temp
        st.success("Master List Loaded Successfully!")

    st.divider()
    st.header("📐 Calibration Settings")
    ref_px = st.number_input("Reference Pixels", value=100.0)
    ref_m = st.number_input("Actual Meters", value=1.0)
    scale = ref_m / ref_px
    
    st.header("🛠️ Tool Selection")
    draw_mode = st.radio("Drawing Mode:", ["line", "rect"])
    
    st.subheader("🧱 Constant Dimensions")
    c_breath = st.number_input("Breath (Width)", value=0.0, step=0.01)
    c_depth = st.number_input("Depth/Height", value=0.0, step=0.1)
    
    pdf_file = st.file_uploader("Upload PDF Plan", type=['pdf'])
    page_num = st.number_input("Page Number", 1, 100, 1)

# --- Main App Interface ---
if pdf_file:
    pdf_file.seek(0)
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    page = doc.load_page(page_num - 1)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
    img = Image.open(io.BytesIO(pix.tobytes()))
    doc.close()
    
    display_height = int(img.height * (1000 / img.width))
    col_n1, col_n2, col_n3 = st.columns([0.2, 0.5, 0.3])
    
    with col_n1:
        u_item_no = st.text_input("Enter Item No:", "1")
    with col_n2:
        custom_name = st.text_input("Location/Description:", "External Wall")
    with col_n3:
        manual_l = st.number_input("📏 Manual Length (Optional):", value=0.0, step=0.01)

    # Auto-Clear logic when Item No or Description changes
    if u_item_no != st.session_state.last_item_no or custom_name != st.session_state.last_description:
        st.session_state.canvas_key += 1
        st.session_state.last_item_no = u_item_no
        st.session_state.last_description = custom_name
        st.rerun()

    # Master Data Lookup
    full_desc, f_unit, f_rate = "", "", 0.0
    if not st.session_state.master_data.empty:
        try:
            t_col = 'item no' if 'item no' in st.session_state.master_data.columns else st.session_state.master_data.columns[0]
            match = st.session_state.master_data[st.session_state.master_data[t_col].astype(str) == str(u_item_no)]
            if not match.empty:
                full_desc = match.iloc[0].get('description of item', match.iloc[0].get('description', ""))
                f_unit = match.iloc[0].get('unit', "")
                f_rate = match.iloc[0].get('rate', 0.0)
        except: pass

    # Drawable Canvas
    from PIL import Image
    import numpy as np

    if img is not None:
        img_for_canvas = Image.fromarray(img.astype('uint8')) if isinstance(img, np.ndarray) else img
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#FF0000",
            background_image=img_for_canvas,
            height=display_height,
            width=1000,
            drawing_mode=draw_mode,
            update_streamlit=True,
            key=f"mirza_v49_{st.session_state.canvas_key}",
        )
            item_rate = float(f_rate) if f_rate else 0.0
            
            # 1. Remove previous total for this item to recalculate
            st.session_state.final_report = st.session_state.final_report[~(st.session_state.final_report['Description'] == f"Total of Item {u_item_no}")]
            
            # 2. Find group position and insert
            existing_indices = st.session_state.final_report.index[st.session_state.final_report['Item No'].astype(str) == str(u_item_no)].tolist()
            if not existing_indices:
                # New Item: Add Header (Rate is empty in header now)
                header = pd.DataFrame([{
                    'Item No': u_item_no, 'Description': full_desc, 'Nos': None, 'Length': None, 'Breath': None, 'Depth': None, 'Quantity': None, 'Unit': f_unit, 'Rate': "", 'Total Quantity': None, 'Amount': None
                }])
                st.session_state.final_report = pd.concat([st.session_state.final_report, header, edited_df], ignore_index=True)
            else:
                # Existing Item: Insert after last entry in group
                last_pos = existing_indices[-1] + 1
                while last_pos < len(st.session_state.final_report) and st.session_state.final_report.iloc[last_pos]['Item No'] == "":
                    last_pos += 1
                st.session_state.final_report = pd.concat([st.session_state.final_report.iloc[:last_pos], edited_df, st.session_state.final_report.iloc[last_pos:]], ignore_index=True)
            
            # 3. Add Summary Row (Total Qty, Rate, and Amount)
            f_df = st.session_state.final_report
            h_idx = f_df.index[f_df['Item No'].astype(str) == str(u_item_no)].tolist()[0]
            curr_sum = 0.0
            p = h_idx + 1
            while p < len(f_df) and f_df.iloc[p]['Item No'] == "":
                val = f_df.iloc[p]['Quantity']
                if pd.notnull(val): curr_sum += float(val)
                p += 1
            
            # Summary Row: Rate and Amount are placed here together
            total_row = pd.DataFrame([{
                'Item No': "", 'Description': f"Total of Item {u_item_no}", 'Nos': None, 'Length': None, 'Breath': None, 'Depth': None, 'Quantity': None, 'Unit': f_unit, 'Rate': item_rate, 'Total Quantity': round(curr_sum, 3), 'Amount': round(curr_sum * item_rate, 2)
            }])
            st.session_state.final_report = pd.concat([f_df.iloc[:p], total_row, f_df.iloc[p:]], ignore_index=True)

            st.session_state.canvas_key += 1
            st.success(f"Item {u_item_no} saved and locked!")
            st.rerun()

# --- Final Report Display ---
if not st.session_state.final_report.empty:
    st.divider()
    st.subheader("📊 Final Takeoff Report (MB Sheet)")
    st.dataframe(st.session_state.final_report, use_container_width=True, hide_index=True)
    
    towrite = io.BytesIO()
    st.session_state.final_report.to_excel(towrite, index=False, engine='openpyxl')
    st.download_button("📥 Download Final Excel", data=towrite, file_name="MIRZA_Estimate_Report.xlsx")

if st.button("🗑️ Clear Entire Report"):
    st.session_state.final_report = pd.DataFrame(columns=['Item No', 'Description', 'Nos', 'Length', 'Breath', 'Depth', 'Quantity', 'Unit', 'Rate', 'Total Quantity', 'Amount'])
    st.rerun()
