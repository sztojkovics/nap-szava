import streamlit as st
import pandas as pd
from datetime import datetime
import unicodedata
from io import StringIO

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

st.header("🧹 Manuális szűrés és CSV frissítés")

# --- Fájlfeltöltés ---
uploaded_file = st.file_uploader("Töltsd fel az eredeti CSV-t", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    st.subheader("🔍 Szűrés kulcsszóra")
    filter_text = st.text_input("Adj meg egy kulcsszót (kis/nagybetű mindegy):", "")

    # --- Szűrés ---
    if filter_text:
        filtered_df = df[df.astype(str).apply(lambda row: row.str.contains(filter_text, case=False, na=False)).any(axis=1)]
    else:
        filtered_df = df.copy()

    st.caption(f"{len(filtered_df)} sor megjelenítve a {len(df)}-ből.")

    # --- Select All / Deselect All ---
    select_all = st.checkbox("✅ Mindent kijelöl / kijelölés törlése")

    st.write("Jelöld ki a törlendő sorokat:")

    to_delete = []

    for i, row in filtered_df.iterrows():
        checked = st.checkbox(
            f"{row.get('szó', '')} – {row.get('beküldte', '')}",
            key=f"chk_{i}",
            value=select_all,
        )
        if checked:
            to_delete.append(row.name)

    # --- Törlés gomb ---
    if st.button("🗑️ Kijelölt sorok törlése"):
        df = df.drop(to_delete).reset_index(drop=True)
        st.success(f"{len(to_delete)} sor törölve. Új méret: {len(df)} sor.")
        st.dataframe(df)

        # --- Letöltés ---
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Letisztított CSV letöltése",
            data=csv,
            file_name="nap_szava_cleaned.csv",
            mime="text/csv",
        )
