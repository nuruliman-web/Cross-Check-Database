import streamlit as st
import pandas as pd
from thefuzz import fuzz
import os

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Cross-Check APU PPT", layout="wide")

st.title("🔍 Cross-Check Database Multi-Parameter")
st.write("Bandingkan Data Internal Anda dengan Database Pemerintah secara otomatis.")

# 2. FITUR UPLOAD FILE
col1, col2 = st.columns(2)
with col1:
    st.info("### 📂 1. Upload Data Internal")
    file_internal = st.file_uploader("Upload file Excel Anda (Data Nasabah)", type=['xlsx'], key="internal")
with col2:
    st.success("### 📂 2. Upload Database Pemerintah")
    file_pemerintah = st.file_uploader("Upload file Database Pemerintah (DTTOT/JUDOL/dll)", type=['xlsx'], key="gov")

# 3. PROSES DATA JIKA KEDUA FILE SUDAH DIUPLOAD
if file_internal and file_pemerintah:
    # Membaca Data
    df_internal = pd.read_excel(file_internal)
    dict_pemerintah = pd.read_excel(file_pemerintah, sheet_name=None) 
    
    st.divider()
    st.subheader("⚙️ Mapping Kolom Data Internal")
    st.caption("Sesuaikan nama kolom di file Anda agar sistem tahu mana yang NIK, Nama, dsb.")
    
    # Menu Mapping Kolom
    cols = df_internal.columns.tolist()
    c1, c2, c3, c4 = st.columns(4)
    with c1: col_nama = st.selectbox("Pilih Kolom Nama", cols)
    with c2: col_nik = st.selectbox("Pilih Kolom NIK", cols)
    with c3: col_tmpt = st.selectbox("Pilih Kolom Tempat Lahir", cols)
    with c4: col_tgl = st.selectbox("Pilih Kolom Tanggal Lahir", cols)

    # Pengaturan Slider di Sidebar
    threshold = st.sidebar.slider("Ambang Kemiripan Nama (%)", 50, 100, 85)
    st.sidebar.write("Semakin tinggi %, semakin ketat pencarian nama.")

    if st.button("🚀 Mulai Cross-Check Sekarang"):
        found_match_total = False
        progress_bar = st.progress(0)
        total_rows = len(df_internal)

        # Iterasi setiap baris di data internal
        for i, row_int in df_internal.iterrows():
            # Update progress bar
            progress_bar.progress((i + 1) / total_rows)
            
            q_nama = str(row_int[col_nama]).strip().lower()
            q_nik = str(row_int[col_nik]).strip().lower()
            q_tmpt = str(row_int[col_tmpt]).strip().lower()
            q_tgl = str(row_int[col_tgl]).strip().lower()

            # Cari di setiap sheet database pemerintah
            for sheet_name, df_gov in dict_pemerintah.items():
                
                def hitung_skor(row_gov):
                    # 1. Cek NIK (Priority - Exact Match)
                    for val_gov in row_gov:
                        if str(val_gov).strip().lower() == q_nik and q_nik != "nan":
                            return 100, "NIK Cocok (Exact)"
                    
                    # 2. Cek Nama (Fuzzy Match - Token Sort Ratio)
                    skor_nama_max = 0
                    for val_gov in row_gov:
                        if pd.notna(val_gov):
                            skor = fuzz.token_sort_ratio(q_nama, str(val_gov).lower())
                            if skor > skor_nama_max:
                                skor_nama_max = skor
                    
                    if skor_nama_max >= threshold:
                        return skor_nama_max, "Nama Mirip"
                    
                    return 0, "-"

                # Eksekusi pengecekan per baris
                temp_gov = df_gov.copy()
                temp_gov[['Skor (%)', 'Status Match']] = temp_gov.apply(lambda r: pd.Series(hitung_skor(r)), axis=1)
                
                # Ambil hasil yang cocok saja
                matches = temp_gov[temp_gov['Skor (%)'] >= threshold]
                
                if not matches.empty:
                    found_match_total = True
                    # Tampilkan hasil dalam expander per orang
                    with st.expander(f"🚩 TERDETEKSI: {q_nama.upper()} pada Sheet [{sheet_name}]"):
                        st.warning(f"Data Internal: {q_nama.upper()} | NIK: {q_nik} | TTL: {q_tmpt.upper()}, {q_tgl}")
                        # Rapikan kolom hasil agar skor di depan
                        prio = ['Skor (%)', 'Status Match']
                        cols_order = prio + [c for c in matches.columns if c not in prio]
                        st.dataframe(matches[cols_order].sort_values('Skor (%)', ascending=False))

        if not found_match_total:
            st.success("✅ Selesai! Tidak ada data yang cocok ditemukan (Data Aman).")
        else:
            st.error("⚠️ Proses selesai. Periksa hasil temuan di atas.")
else:
    st.info("💡 Menunggu kedua file diupload untuk memulai mapping kolom.")
