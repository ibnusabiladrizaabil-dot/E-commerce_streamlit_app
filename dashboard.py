import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from matplotlib import ticker

# ==============================================================================
# 1. KONFIGURASI HALAMAN & FUNGSI LOAD DATA
# ==============================================================================
st.set_page_config(
    page_title="E-Commerce Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Judul Dashboard
st.title("📊 E-Commerce Business Insights Dashboard")
st.markdown("Dashboard ini menampilkan hasil analisis performa kategori produk dan dampak logistik terhadap kepuasan pelanggan.")

@st.cache_data
def load_data():
    """
    Memuat data dari all_data.csv dan mengubah kolom tanggal menjadi datetime.
    """
    try:
        # Membaca file CSV
        df = pd.read_csv("all_data.csv")
        
        # Konversi kolom tanggal (penting untuk filter & perhitungan delay)
        date_cols = [
            'order_purchase_timestamp', 
            'order_delivered_customer_date', 
            'order_estimated_delivery_date'
        ]
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
        return df
    except FileNotFoundError:
        st.error("File 'all_data.csv' tidak ditemukan. Pastikan Anda telah menjalankan kode penggabungan data sebelumnya.")
        return None

# Load Data Utama
all_df = load_data()

# Jika data gagal dimuat, hentikan aplikasi
if all_df is None:
    st.stop()

# ==============================================================================
# 2. SIDEBAR (FILTER RENTANG WAKTU)
# ==============================================================================
with st.sidebar:
    st.header("📅 Filter Waktu")
    
    # Ambil tanggal min dan max dari data
    min_date = all_df['order_purchase_timestamp'].min().date()
    max_date = all_df['order_purchase_timestamp'].max().date()

    # --- PERBAIKAN LAYOUT DI SINI ---
    # Menggunakan st.columns(2) agar input tanggal berdampingan (kecil)
    # bukan bertumpuk ke bawah
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "Mulai Dari",
            min_value=min_date,
            max_value=max_date,
            value=min_date
        )

    with col2:
        end_date = st.date_input(
            "Sampai",
            min_value=min_date,
            max_value=max_date,
            value=max_date
        )

    # Validasi Tanggal
    if start_date > end_date:
        st.error("Tanggal 'Mulai' tidak boleh lebih besar dari 'Sampai'.")
        st.stop()

    st.caption(f"Data tersedia: {min_date} s/d {max_date}")

# Filter data berdasarkan input user
# Konversi ke datetime64[ns] untuk filtering pandas
main_df = all_df[
    (all_df['order_purchase_timestamp'].dt.date >= start_date) & 
    (all_df['order_purchase_timestamp'].dt.date <= end_date)
]

# ==============================================================================
# 3. TOP METRICS (KPI)
# ==============================================================================
st.markdown("### Ringkasan Performa")
col1, col2, col3 = st.columns(3)

with col1:
    # Menghitung Revenue (Hanya yang status delivered/selesai)
    total_revenue = main_df[main_df['order_status'] == 'delivered']['price'].sum()
    st.metric("Total Revenue", f"{total_revenue:,.0f}")

with col2:
    total_order = main_df['order_id'].nunique()
    st.metric("Total Pesanan", f"{total_order:,}")

with col3:
    avg_score = main_df['review_score'].mean()
    st.metric("Rata-rata Skor Review", f"{avg_score:.2f} / 5.0")

st.markdown("---")

# ==============================================================================
# 4. VISUALISASI PERTANYAAN 1: REVENUE vs CANCELLATION RATE
# ==============================================================================
st.header("1. Analisis Kategori Produk")
st.subheader("Revenue Tertinggi vs Tingkat Pembatalan")

# --- Pengolahan Data ---
# A. Hitung Revenue per Kategori
rev_df = main_df[main_df['order_status'] == 'delivered'].groupby('product_category_name_english')['price'].sum().reset_index()
rev_df.rename(columns={'price': 'total_revenue'}, inplace=True)

# B. Hitung Rate Pembatalan per Kategori
# Total pesanan per kategori
total_orders_cat = main_df.groupby('product_category_name_english')['order_id'].nunique().reset_index()
total_orders_cat.rename(columns={'order_id': 'total_orders'}, inplace=True)

# Pesanan batal per kategori
cancel_df = main_df[main_df['order_status'].isin(['canceled', 'unavailable'])].groupby('product_category_name_english')['order_id'].nunique().reset_index()
cancel_df.rename(columns={'order_id': 'canceled_orders'}, inplace=True)

# Gabungkan data
q1_df = pd.merge(rev_df, total_orders_cat, on='product_category_name_english', how='left')
q1_df = pd.merge(q1_df, cancel_df, on='product_category_name_english', how='left')
q1_df['canceled_orders'] = q1_df['canceled_orders'].fillna(0) # Isi 0 jika tidak ada pembatalan

# Hitung Persentase
q1_df['cancellation_rate'] = (q1_df['canceled_orders'] / q1_df['total_orders']) * 100

# Ambil Top 10 Kategori berdasarkan Revenue
top_10_df = q1_df.sort_values(by='total_revenue', ascending=False).head(10)

# --- Visualisasi Dual Axis ---
fig1, ax1 = plt.subplots(figsize=(12, 6))

# Bar Chart (Revenue)
sns.barplot(x='product_category_name_english', y='total_revenue', data=top_10_df, color='skyblue', ax=ax1, label='Revenue')
ax1.set_ylabel('Total Revenue', color='blue', fontsize=12, fontweight='bold')
ax1.tick_params(axis='y', labelcolor='blue')
ax1.set_xlabel('Kategori Produk', fontsize=12)
ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='right')

# Format angka sumbu Y menjadi format ribuan (comma separated)
ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: '{:,.0f}'.format(x)))

# Line Chart (Cancellation Rate)
ax2 = ax1.twinx()
sns.lineplot(x='product_category_name_english', y='cancellation_rate', data=top_10_df, color='red', marker='o', linewidth=3, ax=ax2, label='Cancel Rate')
ax2.set_ylabel('Cancellation Rate (%)', color='red', fontsize=12, fontweight='bold')
ax2.tick_params(axis='y', labelcolor='red')
ax2.set_ylim(0, top_10_df['cancellation_rate'].max() * 1.5) # Memberi ruang lebih di atas

st.pyplot(fig1)

# Penjelasan Insight
with st.expander("💡 Lihat Penjelasan Insight"):
    st.write("""
    * **Health & Beauty** dan **Watches & Gifts** adalah penyumbang pendapatan terbesar bagi perusahaan.
    * Kategori **Bed, Bath, Table** memiliki tingkat pembatalan yang sangat rendah (garis merah di bawah), menandakan performa operasional yang baik.
    * Perhatikan kategori dengan garis merah yang menanjak (misalnya **Toys** atau **Auto**), ini mengindikasikan risiko pembatalan yang lebih tinggi meskipun pendapatannya besar.
    """)

st.markdown("---")

# ==============================================================================
# 5. VISUALISASI PERTANYAAN 2: DELIVERY DELAY vs REVIEW SCORE
# ==============================================================================
st.header("2. Analisis Kepuasan Pelanggan")
st.subheader("Pengaruh Keterlambatan Pengiriman terhadap Skor Ulasan")

# --- Pengolahan Data ---
# Filter data yang valid (delivered & punya tanggal)
q2_df = main_df[
    (main_df['order_status'] == 'delivered') & 
    (main_df['order_delivered_customer_date'].notnull()) & 
    (main_df['order_estimated_delivery_date'].notnull())
].copy()

# Hitung selisih hari (Delay)
q2_df['delay_days'] = (q2_df['order_delivered_customer_date'] - q2_df['order_estimated_delivery_date']).dt.days

# Kategorisasi Status
q2_df['delivery_status'] = q2_df['delay_days'].apply(
    lambda x: 'Terlambat (Late)' if x > 0 else 'Tepat Waktu (On Time)'
)

# Hitung Rata-rata Skor
score_summary = q2_df.groupby('delivery_status')['review_score'].mean()

# --- Layout Kolom ---
col_chart, col_text = st.columns([2, 1])

with col_chart:
    # Visualisasi Bar Chart Sederhana
    fig2, ax = plt.subplots(figsize=(8, 5))
    colors = ["#e74c3c", "#2ecc71"] # Merah, Hijau
    
    # Plotting
    sns.barplot(
        x='delivery_status', 
        y='review_score', 
        data=q2_df, 
        order=['Terlambat (Late)', 'Tepat Waktu (On Time)'], 
        palette=colors, 
        errorbar=None, # Hilangkan error bar agar lebih bersih
        ax=ax
    )
    
    # Menambahkan label angka di atas batang
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.2f}', 
                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                    ha = 'center', va = 'center', 
                    xytext = (0, 10), 
                    textcoords = 'offset points',
                    fontweight='bold', fontsize=12)
    
    ax.set_ylim(0, 5.5) # Batas skor 5
    ax.set_ylabel("Rata-rata Review Score (1-5)")
    ax.set_xlabel("Status Pengiriman")
    st.pyplot(fig2)

with col_text:
    st.info("📌 Key Takeaways")
    
    late_score = score_summary.get('Terlambat (Late)', 0)
    ontime_score = score_summary.get('Tepat Waktu (On Time)', 0)
    
    st.metric("Skor: Tepat Waktu", f"{ontime_score:.2f}")
    st.metric("Skor: Terlambat", f"{late_score:.2f}", delta=f"{late_score - ontime_score:.2f}")
    
    st.write(f"""
    Terdapat penurunan skor yang signifikan sebesar **{ontime_score - late_score:.2f} poin** ketika pengiriman terlambat.
    
    Pelanggan yang menerima barang tepat waktu cenderung memberikan skor nyaris sempurna, sedangkan keterlambatan membuat skor anjlok ke angka **{late_score:.2f}** (kategori buruk/cukup).
    """)

# Footer
st.markdown("---")
st.caption("Dashboard Proyek Analisis Data - Dicoding")