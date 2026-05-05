import streamlit as st
import pandas as pd
from thefuzz import fuzz
import io

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Cross-Check Database Multi-Parameter", layout="wide")

st.title("🔍 Cross-Check Database Multi-Parameter")
st.write("Bandingkan Data Internal dengan Database Pemerintah & Download Hasilnya.")

# 2. FITUR UPLOAD
col1, col2 = st.columns(2)
with col1:
    st.info("### 1. Upload Data Internal")
    file_internal = st.file_uploader("Upload file Excel Anda", type=['xlsx'], key="internal")
with col2:
    st.success("### 2. Upload Database Pemerintah")
    file_pemerintah = st.file_uploader("Upload file Database Pemerintah", type=['xlsx'], key="gov")

# 3. PROSES DATA
if file_internal and file_pemerintah:
    df_internal = pd.read_excel(file_internal)
    dict_pemerintah = pd.read_excel(file_pemerintah, sheet_name=None)
    
    st.divider()
    st.subheader("⚙️ Mapping Kolom Data Internal")
    cols = df_internal.columns.tolist()
    c1, c2, c3, c4 = st.columns(4)
    with c1: col_nama = st.selectbox("Kolom Nama", cols)
    with c2: col_nik = st.selectbox("Kolom NIK", cols)
    with c3: col_tmpt = st.selectbox("Kolom Tempat Lahir", cols)
    with c4: col_tgl = st.selectbox("Kolom Tanggal Lahir", cols)

    threshold = st.sidebar.slider("Ambang Kemiripan Nama (%)", 50, 100, 85)

    if st.button("🚀 Mulai Cross-Check & Siapkan Download"):
        all_matches = [] # List untuk menampung semua temuan
        progress_bar = st.progress(0)
        total_rows = len(df_internal)

        for i, row_int in df_internal.iterrows():
            progress_bar.progress((i + 1) / total_rows)
            q_nama = str(row_int[col_nama]).strip().lower()
            q_nik = str(row_int[col_nik]).strip().lower()

            for sheet_name, df_gov in dict_pemerintah.items():
                def hitung_skor(row_gov):
                    # Cek NIK Exact
                    for val_gov in row_gov:
                        if str(val_gov).strip().lower() == q_nik and q_nik != "nan":
                            return 100, "NIK Cocok"
                    # Cek Nama Fuzzy
                    skor_max = 0
                    for val_gov in row_gov:
                        if pd.notna(val_gov):
                            s = fuzz.token_sort_ratio(q_nama, str(val_gov).lower())
                            if s > skor_max: skor_max = s
                    if skor_max >= threshold: return skor_max, "Nama Mirip"
                    return 0, "-"

                temp_gov = df_gov.copy()
                temp_gov[['Skor (%)', 'Status']] = temp_gov.apply(lambda r: pd.Series(hitung_skor(r)), axis=1)
                
                # Ambil yang Match
                matches = temp_gov[temp_gov['Skor (%)'] >= threshold].copy()
                if not matches.empty:
                    # Tambahkan info data internal ke hasil match untuk laporan
                    matches['Data_Internal_Nama'] = q_nama.upper()
                    matches['Data_Internal_NIK'] = q_nik
                    matches['Ditemukan_di_Sheet'] = sheet_name
                    all_matches.append(matches)

        if all_matches:
            # Gabungkan semua temuan jadi satu tabel besar
            final_report = pd.concat(all_matches, ignore_index=True)
            
            # Tampilkan Ringkasan
            st.error(f"⚠️ Ditemukan {len(final_report)} indikasi kecocokan!")
            st.dataframe(final_report)

            # FITUR DOWNLOAD EXCEL
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                final_report.to_excel(writer, index=False, sheet_name='Hasil_Screening')
            
            st.download_button(
                label="📥 Download Hasil Screening (Excel)",
                data=output.getvalue(),
                file_name="Hasil_Screening_Lengkap.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("✅ Selesai! Tidak ada data yang cocok ditemukan.")
else:
    st.info("Upload kedua file untuk memulai.")
