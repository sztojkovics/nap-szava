import streamlit as st
import pandas as pd
from datetime import datetime
import unicodedata
from io import StringIO
import math

FILENAME = "nap_szava.csv"

def remove_accents(text):
    if not isinstance(text, str):
        return text
    nfkd = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()

# --- Adatbetöltés ---
@st.cache_data
def load_data():
    try:
        return pd.read_csv(FILENAME, parse_dates=["dátum"])
    except FileNotFoundError:
        return pd.DataFrame(columns=["dátum", "szó", "beküldő"])

df = load_data()

# --- Címsor ---
st.set_page_config(page_title="A Nap Szava", page_icon="🌞", layout="centered")
st.title("🌞 A Nap Szava")
st.markdown("Tartsd számon, hogy melyik napon mi volt a nap szava – és ki küldte be!")

# --- Szóra keresés ---
st.header("🔍 Keresés szóra")
szo = st.text_input("Adj meg egy szót:")
if szo:
    df["szó_normalizalt"] = df["szó"].astype(str).apply(remove_accents)
    szo_norm = remove_accents(szo)
    talalatok = df[df["szó_normalizalt"].str.contains(szo_norm, na=False)].drop('szó_normalizalt', axis=1)
    df = df.drop('szó_normalizalt', axis=1)
    if talalatok.empty:
        st.info(f"❌ A '{szo}' szó még nem szerepelt.")
    else:
        st.success(f"✅ A '{szo}' szó előfordulásai:")
        st.dataframe(
            talalatok.sort_values("dátum", ascending=False)
                      .reset_index(drop=True)
        )

# --- Napra keresés ---
st.header("📅 Keresés napra")
honap = st.number_input("Hónap:", min_value=1, max_value=12, value=datetime.now().month)
nap = st.number_input("Nap:", min_value=1, max_value=31, value=datetime.now().day)

if st.button("Mutasd!"):
    df["dátum"] = pd.to_datetime(df["dátum"])
    talalatok = df[(df["dátum"].dt.month == honap) & (df["dátum"].dt.day == nap)]
    if talalatok.empty:
        st.info("Ezen a napon még nem volt szó.")
    else:
        st.success(f"✅ Szavak {honap:02d}-{nap:02d} napokon:")
        st.dataframe(
            talalatok.sort_values("dátum", ascending=False)
                      .reset_index(drop=True)
        )

st.title("Szólista szűrő")

# --- CSV feltöltése ---
uploaded_file = st.file_uploader("Tölts fel egy CSV fájlt", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("Szűrési lehetőségek")

    # Szűrőmező
    filter_text = st.text_input("Szűrés (részszóra keresés):", "")

    # Csak a szűrőnek megfelelő sorok
    if filter_text:
        filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(filter_text, case=False, na=False)).any(axis=1)]
    else:
        filtered_df = df.copy()

    # Lapozás beállításai
    rows_per_page = 100
    total_pages = math.ceil(len(filtered_df) / rows_per_page)
    if "page" not in st.session_state:
        st.session_state.page = 1

    # Lapozógombok
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 8])
    with col1:
        if st.button("<<") and st.session_state.page > 1:
            st.session_state.page = 1
    with col2:
        if st.button("<") and st.session_state.page > 1:
            st.session_state.page -= 1
    with col3:
        st.markdown(f"**{st.session_state.page}/{total_pages}**")
    with col4:
        if st.button(">") and st.session_state.page < total_pages:
            st.session_state.page += 1
    with col5:
        if st.button(">>") and st.session_state.page < total_pages:
            st.session_state.page = total_pages

    # Aktuális oldal tartalma
    start_row = (st.session_state.page - 1) * rows_per_page
    end_row = start_row + rows_per_page
    current_df = filtered_df.iloc[start_row:end_row]

    # Ellenőrző mezők
    st.subheader("Jelöld be a törlendő sorokat")
    selected_rows = st.multiselect(
        "Válaszd ki a törlendő sorokat (index alapján):",
        options=current_df.index.tolist()
    )

    # Törlés
    if st.button("Kijelölt sorok törlése"):
        df = df.drop(selected_rows)
        st.success(f"{len(selected_rows)} sor törölve.")
        st.session_state.page = 1

    # Stílus – fix szélesség, sortörés
    st.markdown("""
    <style>
    .dataframe td {
        max-width: 400px;
        white-space: normal;
        word-wrap: break-word;
    }
    table {
        table-layout: fixed;
        width: 100%;
    }
    th {
        text-align: left !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.dataframe(current_df, use_container_width=True)

    # Frissített CSV letöltése
    st.download_button(
        label="Frissített CSV letöltése",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name="frissitett_szavak.csv",
        mime="text/csv"
    )
