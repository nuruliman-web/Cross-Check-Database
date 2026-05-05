import streamlit as st
import pandas as pd
from thefuzz import fuzz
import io

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Cross-Check Database APU PPT", layout="wide")

st.title("🔍 Cross-Check Database Multi-Parameter")
st.write("Urutan Laporan: Data Internal ➔ Info Kemiripan ➔ Data Eksternal")

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
    # Membaca sheet pertama dari database eksternal
    df_pemerintah = pd.read_excel(file_pemerintah, sheet_name=0) 
    
    st.divider()
    st.subheader("⚙️ Mapping Kolom Data Internal")
    cols_int = df_internal.columns.tolist()
    c1, c2, c3, c4 = st.columns(4)
    with c1: col_nama = st.selectbox("Kolom Nama", cols_int)
    with c2: col_nik = st.selectbox("Kolom NIK", cols_int)
    with c3: col_tmpt = st.selectbox("Kolom Tempat Lahir", cols_int)
    with c4: col_tgl = st.selectbox("Kolom Tanggal Lahir", cols_int)

    threshold = st.sidebar.slider("Ambang Kemiripan Nama (%)", 50, 100, 85)

    if st.button("🚀 Mulai Cross-Check & Siapkan Download"):
        all_results = [] 
        progress_bar = st.progress(0)
        total_rows = len(df_internal)

        for i, row_int in df_internal.iterrows():
            progress_bar.progress((i + 1) / total_rows)
            
            q_nama = str(row_int[col_nama]).strip().lower()
            q_nik = str(row_int[col_nik]).strip().lower()

            def check_row_match(row_gov):
                found_cols = []
                max_score = 0
                
                for idx, val_gov in enumerate(row_gov):
                    if pd.isna(val_gov): continue
                    val_str = str(val_gov).strip().lower()
                    
                    # Cek NIK (Exact)
                    if q_nik != "nan" and q_nik != "" and q_nik == val_str:
                        max_score = 100
                        found_cols.append(f"Kolom ke-{idx+1} (NIK)")
                    
                    # Cek Nama (Fuzzy)
                    score = fuzz.token_sort_ratio(q_nama, val_str)
                    if score >= threshold:
                        if score > max_score: max_score = score
                        found_cols.append(f"Kolom ke-{idx+1} ({score}%)")
                
                return max_score, ", ".join(found_cols)

            # Salin data pemerintah dan beri prefix
            temp_gov = df_pemerintah.copy()
            temp_gov.columns = [f"EKSTERNAL_{c}" for c in temp_gov.columns]
            
            # Hitung skor kemiripan
            res_match = temp_gov.apply(lambda r: pd.Series(check_row_match(r)), axis=1)
            
            # Buat kolom kemiripan
            temp_gov.insert(0, 'STATUS_KOLOM_ALIAS', res_match[1])
            temp_gov.insert(0, 'SKOR_KEMIRIPAN', res_match[0])
            
            # Filter yang cocok
            matches = temp_gov[temp_gov['SKOR_KEMIRIPAN'] >= threshold].copy()
            
            if not matches.empty:
                # Siapkan Data Internal (Kiri) dengan prefix
                internal_data = pd.DataFrame([row_int] * len(matches)).reset_index(drop=True)
                internal_data.columns = [f"INTERNAL_{c}" for c in internal_data.columns]
                
                # Gabungkan: INTERNAL + KEMIRIPAN + EKSTERNAL
                combined = pd.concat([internal_data, matches.reset_index(drop=True)], axis=1)
                all_results.append(combined)

        if all_results:
            final_report = pd.concat(all_results, ignore_index=True)
            
            st.error(f"⚠️ Ditemukan {len(final_report)} baris indikasi kecocokan!")
            st.dataframe(final_report)

            # PROSES DOWNLOAD
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                final_report.to_excel(writer, index=False, sheet_name='Hasil_Screening')
            
            st.download_button(
                label="📥 Download Hasil Lengkap (Excel)",
                data=output.getvalue(),
                file_name="Hasil_Screening_APUPPT.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("✅ Selesai! Tidak ada data yang cocok ditemukan.")
else:
    st.info("💡 Silakan upload kedua file Excel untuk memulai.")
