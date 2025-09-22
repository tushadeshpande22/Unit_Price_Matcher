import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
from io import BytesIO

st.title("📊 Unit Price & Unit Matcher Tool")

# Upload master sheet
master_file = st.file_uploader("Upload Master Sheet", type=["xlsx"], key="master")
if master_file:
    master_df = pd.read_excel(master_file)

    # Normalize column names
    master_df.columns = master_df.columns.str.strip().str.lower()

    # Required columns
    required_master_cols = ["s no.", "item code", "unit", "unit price"]

    if all(col in master_df.columns for col in required_master_cols):
        st.success("✅ Master sheet uploaded successfully!")
    else:
        st.error(f"❌ Master sheet must contain columns: {required_master_cols}")
        master_df = None

# Upload raw sheet
raw_file = st.file_uploader("Upload Raw Sheet", type=["xlsx"], key="raw")
if raw_file:
    raw_df = pd.read_excel(raw_file)

    # Normalize column names
    raw_df.columns = raw_df.columns.str.strip().str.lower()

    if "item code" in raw_df.columns:
        st.success("✅ Raw sheet uploaded successfully!")
    else:
        st.error("❌ Uploaded raw file must contain an 'Item Code' column")
        raw_df = None

# Function for fuzzy matching
def fuzzy_match_item_code(raw_code, master_codes, threshold=50):
    if pd.isna(raw_code):
        return None
    match, score, _ = process.extractOne(
        str(raw_code),
        master_codes,
        scorer=fuzz.token_sort_ratio
    )
    return match if score >= threshold else None

# Process matching
if st.button("🔍 Match & Get Prices"):
    if master_file and raw_file and master_df is not None and raw_df is not None:
        master_codes = master_df["item code"].astype(str).tolist()

        # ✅ Aggregate master by lowest price
        master_clean = (
            master_df.groupby("item code", as_index=False)
            .agg({"unit": "first", "unit price": "min"})
        )

        # Apply fuzzy matching
        raw_df["matched_code"] = raw_df["item code"].apply(
            lambda x: fuzzy_match_item_code(x, master_clean["item code"].astype(str).tolist())
        )

        # Merge on matched code (bring unit + price)
        merged = raw_df.merge(
            master_clean[["item code", "unit", "unit price"]],
            left_on="matched_code",
            right_on="item code",
            how="left"
        )

        st.write("### ✅ Matched Data Preview:")
        st.dataframe(merged.head())

        # Download updated sheet (in memory)
        output = BytesIO()
        merged.to_excel(output, index=False, engine="xlsxwriter")
        output.seek(0)

        st.download_button(
            label="📥 Download Updated File",
            data=output,
            file_name="updated_with_prices_and_units.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )