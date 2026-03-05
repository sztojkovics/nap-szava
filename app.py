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
        return pd.read_csv(FILENAME, parse_dates=["dátum"]).dropna().sort_values("dátum")
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
    df["dátum"] = pd.to_datetime(df["dátum"], format='mixed')
    talalatok = df[(df["dátum"].dt.month == honap) & (df["dátum"].dt.day == nap)]
    if talalatok.empty:
        st.info("Ezen a napon még nem volt szó.")
    else:
        st.success(f"✅ Szavak {honap:02d}-{nap:02d} napokon:")
        st.dataframe(
            talalatok.sort_values("dátum", ascending=False)
                      .reset_index(drop=True)
        )
