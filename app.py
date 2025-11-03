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
    # load dataframe (ne reseteljük az indexet, hogy eredeti index megmaradjon)
    df = pd.read_csv(uploaded_file)
    # biztosítsuk, hogy index egyedi legyen
    df.index = pd.RangeIndex(start=0, stop=len(df), step=1)

    st.subheader("Szűrési beállítások")
    filter_text = st.text_input("Szűrés (részszóra keresés, üres = nincs szűrés):", "")

    # --- filtered view ---
    if filter_text:
        filtered_df = df[df.astype(str).apply(lambda row: row.str.contains(filter_text, case=False, na=False)).any(axis=1)]
    else:
        filtered_df = df.copy()

    # --- pagination settings ---
    rows_per_page = 100
    total_pages = max(1, math.ceil(len(filtered_df) / rows_per_page))
    # clamp current page
    if st.session_state.page < 1:
        st.session_state.page = 1
    if st.session_state.page > total_pages:
        st.session_state.page = total_pages

    start_row = (st.session_state.page - 1) * rows_per_page
    end_row = start_row + rows_per_page
    paged_df = filtered_df.iloc[start_row:end_row].copy()

    st.caption(f"{len(filtered_df)} sor megjelenítve a {len(df)}-ből — oldal: {st.session_state.page}/{total_pages}")

    # --- ensure delete column exists in the paged view (but don't add to master df yet) ---
    if "delete" not in paged_df.columns:
        paged_df["delete"] = False

    # --- compute widths ---
    # Determine approximate widths (in ch) for each visible column (prefer larger for 'szó')
    col_names = list(paged_df.columns)
    col_widths = {}
    for col in col_names:
        max_len = paged_df[col].astype(str).map(len).max() if len(paged_df) > 0 else 0
        if col == "szó":
            # make the 'szó' column relatively wide (~40ch) so ~70% of rows fit
            col_widths[col] = "40ch"
        elif col == "delete":
            col_widths[col] = "6ch"
        else:
            # cap width between 6ch and 30ch based on longest content
            col_widths[col] = f"{min(max(max_len + 2, 6), 30)}ch"

    # --- CSS: stable table, word-wrap for cells, szöveg törése a 'szó' oszlopnál ---
    # We'll set general non-upraking styles and later add per-column widths via nth-child
    st.markdown(
        """
        <style>
        /* fix layout, ne ugráljon */
        div[data-testid="stDataFrame"] table {
            table-layout: fixed;
            width: 100%;
        }
        div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th {
            white-space: normal !important;
            word-wrap: break-word !important;
            overflow-wrap: anywhere !important;
            font-size: 14px !important;
            line-height: 1.3 !important;
            vertical-align: top !important;
        }
        /* biztosítjuk, hogy a táblázat magassága ne változzon (scroll lesz) */
        div[data-testid="stDataFrame"] div[role="grid"] {
            max-height: 600px;
            overflow: auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- Render editable table with a checkbox column config ---
    # Use st.data_editor so user can tick "delete" per row
    column_config = {}
    # add checkbox column config if present
    if "delete" in paged_df.columns:
        column_config["delete"] = st.column_config.CheckboxColumn(
            "Törlés",
            help="Pipáld be, ha ezt a sort törölni szeretnéd.",
            default=False,
            width="6ch"
        )

    edited = st.data_editor(
        paged_df,
        use_container_width=True,
        hide_index=False,
        height=520,  # fix magasság
        column_config=column_config,
        key=f"editor_page_{st.session_state.page}",
        disabled=False,
        num_rows="dynamic",
    )

    # --- Apply CSS column widths based on the current paged_df column order ---
    # The rendered table's first column is the index column, so nth-child starts at 1=index
    # We want to set widths for subsequent columns accordingly.
    css_parts = []
    # Build mapping from column name to its position in displayed table (index + 1)
    # st.data_editor shows index first (th), then the columns in order
    for i, col in enumerate(col_names):
        # nth-child for table header/cell: +1 because index column is first
        nth = i + 2
        w = col_widths.get(col, "10ch")
        css_parts.append(f"div[data-testid='stDataFrame'] table th:nth-child({nth}), div[data-testid='stDataFrame'] table td:nth-child({nth}) {{ width: {w}; max-width: {w}; }}")
    if css_parts:
        st.markdown("<style>" + "".join(css_parts) + "</style>", unsafe_allow_html=True)

    # --- Pagination controls at the bottom ---
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
        # show current/total and small numeric buttons for this + next 4 pages (if available)
        # compute start page for buttons to show current and next 4
        start_btn = st.session_state.page
        btns = []
        for p in range(start_btn, min(start_btn + 5, total_pages + 1)):
            if st.button(str(p), key=f"pgbtn_{p}"):
                st.session_state.page = p
                st.experimental_rerun()
        st.markdown(f"**{st.session_state.page}/{total_pages}**")
    with pager_cols[3]:
        # user requested '>' not working, so use '\>' label
        if st.button(r"\>"):
            if st.session_state.page < total_pages:
                st.session_state.page += 1
                st.experimental_rerun()
    with pager_cols[4]:
        if st.button(">>"):
            st.session_state.page = total_pages
            st.experimental_rerun()

    # --- Deletion: drop from the master df using original indices (edited.index are original indices) ---
    if st.button("🗑️ Kijelölt sorok törlése (az egész adatból)"):
        if "delete" in edited.columns:
            # edited.index are the original indices into df
            to_drop = edited[edited["delete"] == True].index.tolist()
            if len(to_drop) == 0:
                st.warning("Nincsenek kijelölt sorok ezen az oldalon.")
            else:
                # drop from original df
                df = df.drop(index=to_drop).reset_index(drop=True)
                st.success(f"{len(to_drop)} sor törölve az adathalmazból.")
                # after deletion, reset page to 1 to avoid out-of-range page
                st.session_state.page = 1
                # replace filtered_df and paged_df for immediate feedback (not saved to file yet)
                # we rerun so upload state is lost; simplest is to prompt re-upload or instruct user to download new CSV
                st.experimental_rerun()
        else:
            st.warning("A táblázatban nincs 'delete' oszlop.")

    # --- Download updated CSV (from current df) ---
    st.markdown("---")
    st.download_button(
        label="📥 Frissített CSV letöltése",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="nap_szava_cleaned.csv",
        mime="text/csv",
    )
