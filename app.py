import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

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

REQUIRED_COLUMNS = ["NAMA", "NIK", "NISN", "JENIS KELAMIN (male/female)", "TANGGAL LAHIR (YYYY-MM-DD)"]

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
            errors.append(f"⚠️ **Kolom Kosong (Tanpa Data):** {', '.join(empty_cols)}")
    
    if any("Kolom Hilang" in err for err in errors): # Stop only if columns are missing
        return errors, pd.DataFrame()

    # 2. Data Validation
    validation_results = []
    
    for index, row in df.iterrows():
        row_num = index + 5  # Adjusted for Excel row numbering (header at row 4, data starts at row 5)
        row_errors = []
        
        # Helper function to check for illegal characters (quotes, dashes, commas)
        def has_illegal_chars(val):
            return any(char in str(val) for char in ["'", '"', "-", ",", " "])

        # Check Required Fields
        for col in REQUIRED_COLUMNS:
            if pd.isna(row[col]) or str(row[col]).strip() == "":
                row_errors.append(f"Kolom '{col}' tidak boleh kosong")
        
        # Check NIK
        nik = str(row["NIK"]).strip() if not pd.isna(row["NIK"]) else ""
        if nik:
            if has_illegal_chars(nik):
                row_errors.append("NIK tidak boleh mengandung tanda kutip, strip, koma, atau spasi")
            else:
                try:
                    # Convert to clean string (handle scientific notation if any)
                    nik_clean = str(int(float(nik)))
                    if len(nik_clean) != 16:
                        row_errors.append(f"NIK harus 16 digit (terdeteksi {len(nik_clean)} digit)")
                except:
                    row_errors.append("NIK harus berupa angka 16 digit")

        # Check NIS
        nis = str(row["NIS"]).strip() if not pd.isna(row["NIS"]) else ""
        if nis and has_illegal_chars(nis):
            row_errors.append("NIS tidak boleh mengandung tanda kutip, strip, koma, atau spasi")

        # Check NISN
        nisn = str(row["NISN"]).strip() if not pd.isna(row["NISN"]) else ""
        if nisn:
            if has_illegal_chars(nisn):
                row_errors.append("NISN tidak boleh mengandung tanda kutip, strip, koma, atau spasi")
            else:
                try:
                    nisn_clean = str(int(float(nisn)))
                    if len(nisn_clean) != 10:
                        row_errors.append(f"NISN harus 10 digit (terdeteksi {len(nisn_clean)} digit)")
                except:
                    row_errors.append("NISN harus berupa angka 10 digit")

        # Check Phone Number
        phone = str(row["NO TELEPON"]).strip() if not pd.isna(row["NO TELEPON"]) else ""
        if phone and has_illegal_chars(phone):
            row_errors.append("No Telepon tidak boleh mengandung tanda kutip, strip, koma, atau spasi")

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
            validation_results.append({
                "Baris": row_num,
                "Nama": row["NAMA"] if not pd.isna(row["NAMA"]) else "N/A",
                "Masalah": "; ".join(row_errors)
            })

    return errors, pd.DataFrame(validation_results)

uploaded_file = st.file_uploader("Unggah file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Read the file, skipping the first 3 rows of headers/info
        df = pd.read_excel(uploaded_file, header=3)
        
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
                            st.write(err)
                    
                    if not row_errors_df.empty:
                        st.warning(f"Ditemukan {len(row_errors_df)} baris dengan masalah format:")
                        st.dataframe(row_errors_df, width="stretch")
                        
                        # Option to download errors as XLSX
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            row_errors_df.to_excel(writer, index=False, sheet_name='Kesalahan')
                        xlsx_data = output.getvalue()

                        st.download_button(
                            label="Unduh Laporan Kesalahan (XLSX)",
                            data=xlsx_data,
                            file_name="laporan_kesalahan.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
    st.write("- **NIK:** 16 digit angka (tanpa tanda baca)")
    st.write("- **NISN:** 10 digit angka (tanpa tanda baca)")
    st.write("- **No Telepon:** Angka saja (tanpa strip/spasi)")
    st.write("- **Jenis Kelamin:** male / female")
    st.write("- **Tanggal Lahir:** YYYY-MM-DD")

    st.write("---")
    st.header("💡 Panduan Perbaikan")
    with st.expander("Cara Memperbaiki Data"):
        st.markdown("""
        1. **NIK/NISN Hilang Angka Nol:** 
           - Ubah format sel di Excel menjadi **'Text'** sebelum mengetik angka.
           - Pastikan NIK 16 digit dan NISN 10 digit.
        2. **Format Tanggal Salah:**
           - Gunakan format **YYYY-MM-DD** (Contoh: 2010-05-20).
           - Jika otomatis berubah di Excel, ubah format sel menjadi **'Text'**.
        3. **Karakter Ilegal (Kutip, Strip, Koma, Spasi):**
           - Kolom NIK, NIS, NISN, dan No Telepon **hanya boleh berisi angka**.
           - Hapus semua tanda baca atau spasi di dalam kolom tersebut.
        4. **Jenis Kelamin:**
            - Hanya boleh diisi **male** atau **female** (huruf kecil).
         5. **Kolom Hilang atau Kosong:**
            - Jangan mengubah nama header di baris ke-4 template asli.
            - Pastikan kolom tidak dibiarkan kosong seluruhnya jika data tersebut tersedia.
        """)

    st.write("---")
    st.info("Made With Love By Jitara ID")
