import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Indodax", layout="wide")
st.title("Dashboard Market Indodax")

# --- KONFIGURASI DATABASE ---
DB_USER = 'root'
DB_PASS = ''
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'indodax_db'

@st.cache_resource
def init_connection():
    engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    return engine

engine = init_connection()

# --- MENGAMBIL DAFTAR PAIR UNTUK DROPDOWN ---
@st.cache_data(ttl=600)
def get_available_pairs():
    query = "SELECT DISTINCT pair FROM indodax_tickers ORDER BY pair ASC"
    df_pairs = pd.read_sql(query, con=engine)
    return df_pairs['pair'].tolist()

list_pairs = get_available_pairs()

# --- TAMPILAN FILTER ---
st.markdown("### Filter Market")

if not list_pairs:
    st.error("Data pair tidak ditemukan. Pastikan database dan tabel Anda sudah terisi.")
else:
    col1, col2 = st.columns(2)
    with col1:
        # Menampilkan dropdown sesuai nama pair di database
        default_idx = list_pairs.index('btc_idr') if 'btc_idr' in list_pairs else 0
        selected_pair = st.selectbox("Pilih Pair Market", options=list_pairs, index=default_idx)

    with col2:
        limit_data = st.selectbox("Ambil berapa data terakhir?", [100, 500, 1000, 5000])

    # --- MENGAMBIL DATA KHUSUS 1 PAIR ---
    @st.cache_data(ttl=60)
    def load_data(pair, limit):
        # Urutan SELECT disamakan persis dengan phpMyAdmin Anda
        query = f"""
            SELECT id, pair, last_price, high_24h, low_24h, created_at
            FROM indodax_tickers
            WHERE pair = '{pair}'
            ORDER BY created_at DESC
            LIMIT {limit}
        """
        df = pd.read_sql(query, con=engine)

        # Urutkan berdasarkan waktu (lama -> baru) untuk grafik
        df = df.sort_values(by='created_at').reset_index(drop=True)

        # Membuat nilai open simulasi untuk Candlestick
        if not df.empty:
            df['open'] = df['last_price'].shift(1)
            df.loc[0, 'open'] = df.loc[0, 'last_price']

        return df

    df = load_data(selected_pair, limit_data)

    if df.empty:
        st.warning(f"Data untuk pair '{selected_pair}' saat ini kosong.")
    else:
        st.success(f"Menampilkan {len(df)} data terakhir khusus untuk Market: **{selected_pair.upper()}**.")

        # --- TABEL SAMA PERSIS DENGAN PHPMYADMIN ---
        with st.expander("Lihat Tabel Data (Format Sesuai phpMyAdmin)", expanded=True):
            st.dataframe(df.drop(columns=['open']), hide_index=True)

        # --- VISUALISASI GRAFIK KHUSUS 1 PAIR ---
        st.markdown("---")
        st.markdown(f"### Pergerakan Harga: {selected_pair.upper()}")

        tab1, tab2, tab3 = st.tabs([" Candlestick", " Bar Chart", " Line Chart"])

        # 1. Candlestick Chart (Style TradingView)
        with tab1:
            st.subheader(f"Candlestick {selected_pair.upper()}")
            fig_candle = go.Figure(data=[go.Candlestick(
                x=df['created_at'],
                open=df['open'],
                high=df['high_24h'],
                low=df['low_24h'],
                close=df['last_price'],
                name=selected_pair.upper(),
                # Menyesuaikan warna candle ala TradingView
                increasing_line_color='#089981',
                decreasing_line_color='#f23645'
            )])

            # Membersihkan layout dan menyesuaikan background
            fig_candle.update_layout(
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                plot_bgcolor='#131722',   # Background chart gelap
                paper_bgcolor='#131722',  # Background area luar chart
                xaxis=dict(
                    showgrid=False,       # Menghilangkan grid vertikal
                    zeroline=False,
                    linecolor='#2b2b36'
                ),
                yaxis=dict(
                    showgrid=True,        # Grid horizontal tipis untuk panduan harga
                    gridcolor='#2b2b36',
                    zeroline=False,
                    linecolor='#2b2b36'
                ),
                margin=dict(l=10, r=10, b=10, t=40) # Merapatkan jarak tepi
            )
            st.plotly_chart(fig_candle, width="stretch")
        # 2. Bar Chart (Menggunakan last_price dari pair terpilih)
        with tab2:
            st.subheader(f"Bar Chart Harga Terakhir {selected_pair.upper()}")
            fig_bar = px.bar(
                df,
                x='created_at',
                y='last_price',
                color='last_price',
                color_continuous_scale='Blues'
            )
            fig_bar.update_layout(template="plotly_dark")
            st.plotly_chart(fig_bar, width="stretch")

        # 3. Line Chart (Menggunakan last_price dari pair terpilih)
        with tab3:
            st.subheader(f"Trend Harga {selected_pair.upper()}")
            fig_line = px.line(
                df,
                x='created_at',
                y='last_price',
                markers=False
            )
            fig_line.update_traces(line_color='#00ff00')
            fig_line.update_layout(template="plotly_dark")
            st.plotly_chart(fig_line, width="stretch")
            