import streamlit as st
import pandas as pd
from datetime import datetime

FILENAME = "nap_szava.csv"

# --- Adatbetöltés ---
@st.cache_data
def load_data():
    try:
        return pd.read_csv(FILENAME, parse_dates=["datum"])
    except FileNotFoundError:
        return pd.DataFrame(columns=["datum", "szó", "beküldő"])

df = load_data()

# --- Címsor ---
st.set_page_config(page_title="A Nap Szava", page_icon="🌞", layout="centered")
st.title("🌞 A Nap Szava")
st.markdown("Tartsd számon, hogy melyik napon mi volt a nap szava – és ki küldte be!")

# --- Szóra keresés ---
st.header("🔍 Keresés szóra")
szo = st.text_input("Adj meg egy szót:")
if szo:
    talalatok = df[df["szó"].str.lower().str.contains(szo.lower())]
    if talalatok.empty:
        st.info(f"❌ A '{szo}' szó még nem szerepelt.")
    else:
        st.success(f"✅ A '{szo}' szó előfordulásai:")
        st.dataframe(
            talalatok.sort_values("datum", ascending=False)
                      .reset_index(drop=True)
        )

# --- Napra keresés ---
st.header("📅 Keresés napra")
honap = st.number_input("Hónap:", min_value=1, max_value=12, value=datetime.now().month)
nap = st.number_input("Nap:", min_value=1, max_value=31, value=datetime.now().day)

if st.button("Mutasd!"):
    df["datum"] = pd.to_datetime(df["datum"])
    talalatok = df[(df["datum"].dt.month == honap) & (df["datum"].dt.day == nap)]
    if talalatok.empty:
        st.info("Ezen a napon még nem volt szó.")
    else:
        st.success(f"✅ Szavak {honap:02d}-{nap:02d} napokon:")
        st.dataframe(
            talalatok.sort_values("datum", ascending=False)
                      .reset_index(drop=True)
        )

# --- Új szó hozzáadása ---
st.header("➕ Új szó hozzáadása")
uj_szo = st.text_input("Új szó:")
bekuldo = st.text_input("Beküldő neve:")

if st.button("Hozzáadás"):
    if uj_szo and bekuldo:
        uj = pd.DataFrame({
            "datum": [datetime.now().strftime("%Y-%m-%d")],
            "szó": [uj_szo],
            "beküldő": [bekuldo]
        })
        df = pd.concat([df, uj], ignore_index=True)
        df.to_csv(FILENAME, index=False)
        st.success(f"✅ '{uj_szo}' hozzáadva ({bekuldo})")
    else:
        st.warning("Add meg a szót és a beküldőt is!")
