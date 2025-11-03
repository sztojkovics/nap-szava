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

st.header("🧹 Manuális szűrés és CSV frissítés")

st.set_page_config(page_title="Nap szava - Szűrés", layout="wide")

st.header("🧹 Manuális szűrés és CSV frissítés")

# --- Állapot tárolása (pl. utolsó feldolgozott index) ---
if "last_index" not in st.session_state:
    st.session_state.last_index = 0

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

    # --- Lapozás beállítás ---
    page_size = 100
    total_pages = math.ceil(len(filtered_df) / page_size)

    page = st.number_input("Oldalszám", min_value=1, max_value=max(1, total_pages), value=1, step=1)

    start = (page - 1) * page_size
    end = start + page_size

    paged_df = filtered_df.iloc[start:end].copy()

    st.caption(f"{len(filtered_df)} sor megjelenítve a {len(df)}-ből. ({total_pages} oldal)")

    # --- Táblázatos megjelenítés checkboxokkal ---
    st.write("✅ Pipáld ki a törlendő sorokat (több is kijelölhető):")

    edited_df = st.data_editor(
        paged_df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"editor_page_{page}",
        column_config={
            "delete": st.column_config.CheckboxColumn(
                "Törlés",
                help="Pipáld be, ha ezt a sort törölni szeretnéd.",
                default=False,
            )
        },
        hide_index=False
    )

    # --- Sorok törlése ---
    if st.button("🗑️ Kijelölt sorok törlése ebben az oldalban"):
        if "delete" in edited_df.columns:
            delete_indices = edited_df[edited_df["delete"] == True].index
            df = df.drop(delete_indices).reset_index(drop=True)
            st.success(f"{len(delete_indices)} sor törölve.")

            # Frissítjük a session state-et, hogy megjegyezze, hol tartottál
            if len(delete_indices) > 0:
                st.session_state.last_index = delete_indices[-1] + 1

        else:
            st.warning("Nincs kijelölt sor a törléshez.")

        # Frissített CSV letöltése
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Letisztított CSV letöltése",
            data=csv,
            file_name="nap_szava_cleaned.csv",
            mime="text/csv",
        )

    # --- Utolsó feldolgozott sor megjelenítése ---
    if st.session_state.last_index > 0:
        st.info(f"📍 Utolsó feldolgozott sor indexe: {st.session_state.last_index}")
else:
    st.info("📤 Töltsd fel a CSV-t a kezdéshez.")
