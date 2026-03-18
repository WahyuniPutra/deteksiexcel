import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime
from fpdf import FPDF

# Custom PDF class for report generation
class PDFReport(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 16)
        self.cell(0, 10, "Laporan Kesalahan Data Siswa", 0, 1, "C")
        self.ln(5)
        self.set_font("helvetica", "I", 10)
        self.cell(0, 10, f"Tanggal Laporan: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "R")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Halaman {self.page_no()}/{{nb}} - Made With Love By Jitara ID", 0, 0, "C")

def create_pdf(df):
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.alias_nb_pages()
    
    # Define column widths
    col_widths = [15, 45, 60, 70] # Baris, Nama, Masalah, Panduan
    
    # Table Header
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    headers = ["Baris", "Nama", "Masalah", "Panduan Perbaikan"]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1, 0, "C", fill=True)
    pdf.ln()
    
    # Table Content
    pdf.set_font("helvetica", "", 8)
    for _, row in df.iterrows():
        # Get row height based on content
        lines_masalah = pdf.multi_cell(col_widths[2], 5, str(row['Masalah']), split_only=True)
        lines_panduan = pdf.multi_cell(col_widths[3], 5, str(row['Panduan Perbaikan']), split_only=True)
        row_height = max(len(lines_masalah), len(lines_panduan)) * 5
        if row_height < 10: row_height = 10
        
        # Check if row fits on page
        if pdf.get_y() + row_height > 270:
            pdf.add_page()
            # Re-draw header on new page
            pdf.set_font("helvetica", "B", 10)
            pdf.set_fill_color(200, 220, 255)
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, 1, 0, "C", fill=True)
            pdf.ln()
            pdf.set_font("helvetica", "", 8)

        x = pdf.get_x()
        y = pdf.get_y()
        
        pdf.cell(col_widths[0], row_height, str(row['Baris']), 1, 0, "C")
        pdf.cell(col_widths[1], row_height, str(row['Nama'])[:25], 1, 0, "L")
        
        # Multi-cell for wrapped text
        pdf.multi_cell(col_widths[2], 5, str(row['Masalah']), 1, "L")
        pdf.set_xy(x + col_widths[0] + col_widths[1] + col_widths[2], y)
        pdf.multi_cell(col_widths[3], 5, str(row['Panduan Perbaikan']), 1, "L")
        
        pdf.ln(0) # Ensure next row starts at the bottom of the current multi-cell block
        
    return bytes(pdf.output())

st.set_page_config(page_title="Validator Data Siswa", layout="wide")

st.title("📋 Validator Data Siswa")
st.markdown("""
Aplikasi ini digunakan untuk memvalidasi file Excel data siswa sebelum diunggah ke sistem Kelas Digital Huma Betang.
Pastikan file Anda menggunakan format yang sesuai dengan template.
""")

# Define expected columns and their rules
EXPECTED_COLUMNS = [
    "NAMA", "NIK", "NIS", "NISN", "JENIS KELAMIN (male/female)", 
    "TEMPAT LAHIR", "TANGGAL LAHIR (YYYY-MM-DD)", "NAMA ORANG TUA/WALI", 
    "AGAMA", "BAHASA SEHARI-HARI", "KOTA TEMPAT TINGGAL", "ALAMAT", 
    "EMAIL", "NO TELEPON"
]

REQUIRED_COLUMNS = EXPECTED_COLUMNS.copy()

def validate_data(df):
    errors = []
    
    # 1. Check Columns Completeness
    current_columns = df.columns.tolist()
    missing_cols = [col for col in EXPECTED_COLUMNS if col not in current_columns]
    if missing_cols:
        errors.append(f"❌ **Kolom Hilang:** {', '.join(missing_cols)}")
    
    # 2. Check for Entirely Empty Columns
    if not missing_cols:
        empty_cols = [col for col in EXPECTED_COLUMNS if df[col].isnull().all()]
        if empty_cols:
            errors.append(f"❌ **Kolom Kosong (Tanpa Data):** {', '.join(empty_cols)}")
    

    # 3. Check Column Data Types for leading zero preservation
    numeric_cols_to_check = ["NIK", "NIS", "NISN", "NO TELEPON"]
    improperly_formatted_cols = []
    if not missing_cols:
        for col in numeric_cols_to_check:
            # Check if any value in the column is an actual number (int or float) instead of a string
            # This is the most reliable way to detect if the Excel format wasn't "Text"
            has_numeric_values = df[col].apply(lambda x: isinstance(x, (int, float)) and not pd.isna(x)).any()
            if has_numeric_values:
                improperly_formatted_cols.append(col)
        
        if improperly_formatted_cols:
            errors.append(f"format_text:{', '.join(improperly_formatted_cols)}")

    if errors: # Stop if there are any structural errors
        return errors, pd.DataFrame()

    # 2. Data Validation
    validation_results = []
    
    for index, row in df.iterrows():
        row_num = index + 5  # Adjusted for Excel row numbering (header at row 4, data starts at row 5)
        row_errors = []
        
        # Helper function to clean and validate numeric strings (preserving leading zeros)
        def validate_numeric(val, field_name, expected_length=None):
            if pd.isna(val) or str(val).strip() == "":
                return None
            
            # Convert to string and strip
            s_val = str(val).strip()
            
            # Handle cases where pandas reads large numbers as floats (e.g., 1.23e+15 or 123.0)
            if "." in s_val and s_val.replace(".","",1).isdigit():
                try:
                    s_val = str(int(float(s_val)))
                except:
                    pass
            
            if not s_val.isdigit():
                return f"{field_name} hanya boleh berisi angka (tanpa spasi, strip, atau tanda baca)"
            
            if expected_length and len(s_val) != expected_length:
                return f"{field_name} harus {expected_length} digit (terdeteksi {len(s_val)} digit)"
            
            return None

        # Check Required Fields
        for col in REQUIRED_COLUMNS:
            if pd.isna(row[col]) or str(row[col]).strip() == "":
                row_errors.append(f"Kolom '{col}' tidak boleh kosong")
        
        # Check NIK
        nik_err = validate_numeric(row["NIK"], "NIK", 16)
        if nik_err: row_errors.append(nik_err)

        # Check NIS
        nis_err = validate_numeric(row["NIS"], "NIS")
        if nis_err: row_errors.append(nis_err)

        # Check NISN
        nisn_err = validate_numeric(row["NISN"], "NISN", 10)
        if nisn_err: row_errors.append(nisn_err)

        # Check Phone Number
        phone_err = validate_numeric(row["NO TELEPON"], "No Telepon")
        if phone_err: row_errors.append(phone_err)

        # Check Gender
        gender = str(row["JENIS KELAMIN (male/female)"]).strip().lower() if not pd.isna(row["JENIS KELAMIN (male/female)"]) else ""
        if gender and gender not in ["male", "female"]:
            row_errors.append("Jenis Kelamin harus 'male' atau 'female'")
            
        # Check Date Format
        dob = row["TANGGAL LAHIR (YYYY-MM-DD)"]
        if not pd.isna(dob):
            if not isinstance(dob, (datetime, pd.Timestamp)):
                try:
                    pd.to_datetime(dob, format='%Y-%m-%d')
                except:
                    row_errors.append("Format Tanggal Lahir harus YYYY-MM-DD")

        # Check Email
        email = str(row["EMAIL"]).strip() if not pd.isna(row["EMAIL"]) else ""
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            row_errors.append("Format Email tidak valid")

        if row_errors:
            # Generate quick guides for each row based on the errors found
            guides = []
            for err in row_errors:
                if "NIK" in err and "digit" in err:
                    guides.append("NIK harus 16 digit. Gunakan fitur Data > Text to Columns (Step 3: Text) agar angka 0 di depan tidak hilang. Contoh: 0123456789012345")
                elif "NISN" in err and "digit" in err:
                    guides.append("NISN harus 10 digit. Gunakan fitur Data > Text to Columns (Step 3: Text) agar angka 0 di depan tidak hilang. Contoh: 0012345678")
                elif "berisi angka" in err:
                    guides.append("Kolom ini hanya boleh berisi angka murni. Hapus spasi, strip (-), atau tanda baca lainnya. Contoh: 081234567890")
                elif "tidak boleh kosong" in err:
                    guides.append("Kolom ini wajib diisi. Pastikan tidak ada sel yang kosong.")
                elif "Jenis Kelamin" in err:
                    guides.append("Gunakan 'male' (Laki-laki) atau 'female' (Perempuan) dalam huruf kecil. Contoh: male")
                elif "Tanggal Lahir" in err:
                    guides.append("Gunakan format Tahun-Bulan-Tanggal (YYYY-MM-DD). Contoh: 2010-05-20")
                elif "Email" in err:
                    guides.append("Pastikan alamat email lengkap dengan simbol '@' dan domain. Contoh: siswa@gmail.com")
            
            # Format Masalah and Panduan as numbered lists
            formatted_errors = "\n".join([f"{i+1}. {err}" for i, err in enumerate(row_errors)])
            formatted_guides = "\n".join([f"{i+1}. {guide}" for i, guide in enumerate(list(dict.fromkeys(guides)))])
            
            validation_results.append({
                "Baris": row_num,
                "Nama": row["NAMA"] if not pd.isna(row["NAMA"]) else "N/A",
                "Masalah": formatted_errors,
                "Panduan Perbaikan": formatted_guides
            })

    return errors, pd.DataFrame(validation_results)

uploaded_file = st.file_uploader("Unggah file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Trick: Read as object to prevent early inference, and clear any previous session state
        df = pd.read_excel(uploaded_file, header=3, dtype=object)
        
        st.subheader("Preview Data")
        st.dataframe(df.head())

        if st.button("Mulai Validasi"):
            with st.spinner("Memvalidasi data..."):
                general_errors, row_errors_df = validate_data(df)
                
                if not general_errors and row_errors_df.empty:
                    st.success("✅ Semua data sudah sesuai format! Siap untuk diunggah.")
                else:
                    if general_errors:
                        st.error("Ditemukan kesalahan struktur:")
                        for err in general_errors:
                            if err.startswith("format_text:"):
                                cols = err.split(":")[1]
                                st.error(f"❌ **Format Kolom Salah:** Kolom **{cols}** terdeteksi sebagai Angka, bukan Teks.")
                                st.info("**Solusi:** Di Excel, pilih kolom tersebut, ubah format sel menjadi **'Text'**. Lalu gunakan fitur **Data > Text to Columns**, klik **Next** sampai **Step 3**, pilih opsi **'Text'** pada *Column data format*, kemudian klik **Finish**. Ini akan memastikan angka 0 di depan tidak hilang.")
                            else:
                                st.error(err)
                    
                    if not row_errors_df.empty:
                        st.warning(f"Ditemukan {len(row_errors_df)} baris dengan masalah format:")
                        st.dataframe(row_errors_df, width="stretch")
                        
                        # Option to download errors as XLSX
                        output_xlsx = io.BytesIO()
                        with pd.ExcelWriter(output_xlsx, engine='openpyxl') as writer:
                            row_errors_df.to_excel(writer, index=False, sheet_name='Kesalahan')
                        xlsx_data = output_xlsx.getvalue()

                        # Option to download errors as PDF
                        pdf_data = create_pdf(row_errors_df)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📥 Unduh Laporan Kesalahan (XLSX)",
                                data=xlsx_data,
                                file_name=f"laporan_kesalahan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        with col2:
                            st.download_button(
                                label="📥 Unduh Laporan Kesalahan (PDF)",
                                data=pdf_data,
                                file_name=f"laporan_kesalahan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
    except Exception as e:
        st.error(f"Terjadi kesalahan saat membaca file: {e}")
else:
    st.info("Silakan unggah file Excel untuk memulai.")

# Sidebar info
with st.sidebar:
    st.header("Panduan Format")
    st.write("**Kolom Wajib:**")
    for col in REQUIRED_COLUMNS:
        st.write(f"- {col}")
    
    st.write("---")
    st.write("**Ketentuan Khusus:**")
    st.write("- **NIK:** 16 digit angka")
    st.write("- **NISN:** 10 digit angka")
    st.write("- **Jenis Kelamin:** male / female")
    st.write("- **Tanggal Lahir:** YYYY-MM-DD")
    st.write("- **Email:** Format email standar")

    st.write("---")
    st.info("Made With Love By Jitara ID")
