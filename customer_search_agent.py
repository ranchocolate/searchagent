import streamlit as st
import pandas as pd
import re

# Load customer data
@st.cache_data
def load_customers(file_path):
    return pd.read_csv(file_path)

# Search all fields for a match
def search_customers(input_value, customers_df):
    input_value_lower = input_value.lower()
    matches = []

    for _, row in customers_df.iterrows():
        matched_fields = []
        for field, value in row.items():
            if pd.isna(value):
                continue
            if input_value_lower in str(value).lower():
                matched_fields.append(field)
        if matched_fields:
            matches.append((row.to_dict(), matched_fields))

    return matches

# Streamlit UI
st.title("🔎 AI Customer Search Agent")

customers_df = load_customers("customers.csv")
query = st.text_input("Enter any identifier (email, phone, ID, name, etc.)")

if query:
    results = search_customers(query, customers_df)
    if results:
        for customer, fields in results:
            st.markdown("---")
            st.subheader(f"🎯 Match found in: {', '.join(fields)}")
            for k, v in customer.items():
                st.write(f"**{k}**: {v}")
    else:
        st.warning("No matches found.")
