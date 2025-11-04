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

st.set_page_config(page_title="Nap szava - Szűrés", layout="wide")
st.title("Nap szava - manuális tisztítás")

# --- session state init ---
if "page" not in st.session_state:
    st.session_state.page = 1

# --- File upload ---
uploaded_file = st.file_uploader("Tölts fel egy CSV fájlt (datum,szó,beküldő):", type="csv")

if uploaded_file is None:
    st.info("Tölts fel egy CSV fájlt a megkezdéshez.")
else:
    # load dataframe
    df = pd.read_csv(uploaded_file)
    df.index = pd.RangeIndex(start=0, stop=len(df), step=1)

    st.subheader("Szűrési beállítások")
    filter_text = st.text_input("Szűrés (részszóra keresés, üres = nincs szűrés):", "")

    # --- filtered view ---
    if filter_text:
        filtered_df = df[df.astype(str).apply(lambda row: row.str.contains(filter_text, case=False, na=False)).any(axis=1)]
    else:
        filtered_df = df.copy()

    # --- pagination ---
    rows_per_page = 100
    total_pages = max(1, math.ceil(len(filtered_df) / rows_per_page))
    st.session_state.page = min(st.session_state.page, total_pages)
    st.session_state.page = max(st.session_state.page, 1)

    start_row = (st.session_state.page - 1) * rows_per_page
    end_row = start_row + rows_per_page
    paged_df = filtered_df.iloc[start_row:end_row].copy()

    st.caption(f"{len(filtered_df)} sor megjelenítve a {len(df)}-ből — oldal: {st.session_state.page}/{total_pages}")

    # --- add delete column if missing ---
    if "delete" not in paged_df.columns:
        paged_df["delete"] = False

    # --- fix width + no resize CSS ---
    st.markdown("""
        <style>
        /* teljes táblázat fix layout */
        div[data-testid="stDataFrame"] table {
            table-layout: fixed;
            width: 100%;
        }
        /* cellák fix méret, ne törjenek sort, és ha túl hosszú, "..." */
        div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th {
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            font-size: 14px !important;
            line-height: 1.3 !important;
            vertical-align: top !important;
        }
        /* a "szó" oszlop legyen szélesebb */
        div[data-testid="stDataFrame"] table th:nth-child(3),
        div[data-testid="stDataFrame"] table td:nth-child(3) {
            width: 400px !important;
            max-width: 400px !important;
        }
        /* a többi oszlop kisebb */
        div[data-testid="stDataFrame"] table th:nth-child(2),
        div[data-testid="stDataFrame"] table td:nth-child(2),
        div[data-testid="stDataFrame"] table th:nth-child(4),
        div[data-testid="stDataFrame"] table td:nth-child(4),
        div[data-testid="stDataFrame"] table th:nth-child(5),
        div[data-testid="stDataFrame"] table td:nth-child(5) {
            width: 150px !important;
            max-width: 150px !important;
        }
        /* fix magasság, hogy ne ugráljon */
        div[data-testid="stDataFrame"] div[role="grid"] {
            max-height: 600px;
            height: 600px;
            overflow-y: auto;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- editable table ---
    column_config = {
        "delete": st.column_config.CheckboxColumn(
            "Törlés",
            help="Pipáld be, ha ezt a sort törölni szeretnéd.",
            default=False,
            width="6ch"
        )
    }

    edited = st.data_editor(
        paged_df,
        use_container_width=True,
        hide_index=False,
        height=600,
        column_config=column_config,
        key=f"editor_page_{st.session_state.page}",
    )

    # --- pagination controls (bottom) ---
    st.markdown("---")
    pager_cols = st.columns([1,1,2,1,1])
    with pager_cols[0]:
        if st.button("<<"):
            st.session_state.page = 1
            st.experimental_rerun()
    with pager_cols[1]:
        if st.button("<"):
            if st.session_state.page > 1:
                st.session_state.page -= 1
                st.experimental_rerun()
    with pager_cols[2]:
        start_btn = st.session_state.page
        for p in range(start_btn, min(start_btn + 5, total_pages + 1)):
            if st.button(str(p), key=f"pgbtn_{p}"):
                st.session_state.page = p
                st.experimental_rerun()
        st.markdown(f"**{st.session_state.page}/{total_pages}**")
    with pager_cols[3]:
        if st.button(r"\>"):
            if st.session_state.page < total_pages:
                st.session_state.page += 1
                st.experimental_rerun()
    with pager_cols[4]:
        if st.button("\>\>"):
            st.session_state.page = total_pages
            st.experimental_rerun()

    # --- Deletion ---
    if st.button("🗑️ Kijelölt sorok törlése"):
        if "delete" in edited.columns:
            to_drop = edited[edited["delete"] == True].index.tolist()
            if not to_drop:
                st.warning("Nincsenek kijelölt sorok ezen az oldalon.")
            else:
                df = df.drop(index=to_drop).reset_index(drop=True)
                st.success(f"{len(to_drop)} sor törölve.")
                st.session_state.page = 1
                st.experimental_rerun()

    # --- Download updated CSV ---
    st.markdown("---")
    st.download_button(
        label="📥 Frissített CSV letöltése",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="nap_szava_cleaned.csv",
        mime="text/csv",
    )
