import streamlit as st
import pandas as pd
import re
from rapidfuzz import fuzz

# Load customer data
@st.cache_data
def load_customers(file_path):
    return pd.read_csv(file_path)

# Validate individual fields
def is_valid_name(name):
    return bool(re.fullmatch(r"[A-Za-z\s\.\'-]+", name))

def is_valid_email(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))

def is_valid_phone(phone):
    return bool(re.fullmatch(r"\+?\d{8,15}", phone))

st.title("🔎 AI Customer Search & Fraud Detection")

with st.sidebar.expander("🔧 Address Blacklist & Synonyms Configuration", expanded=False):
    # User-editable address blacklist
    address_blacklist_input = st.text_area(
        "Blacklisted Addresses (one per line):",
        value="\n".join([
            "123 fake street",
            "456 fraud strasse"
        ])
    )
    ADDRESS_BLACKLIST = [addr.strip().lower() for addr in address_blacklist_input.strip().splitlines() if addr.strip()]

    # User-editable address synonyms
    synonyms_input = st.text_area(
        "Address Synonyms (format: variant=replacement, one per line):",
        value="\n".join([
            "street=st",
            "st.=st",
            "strasse=str",
            "str.=str",
            "avenue=ave",
            "road=rd",
            "rd.=rd",
            "drive=dr",
            "boulevard=blvd"
        ])
    )
    ADDRESS_SYNONYMS = {}
    for line in synonyms_input.strip().splitlines():
        if "=" in line:
            variant, replacement = line.strip().split("=", 1)
            ADDRESS_SYNONYMS[variant.strip().lower()] = replacement.strip().lower()

# Validation and anomaly detection
def find_invalid_entries(customers_df):
    issues = []
    for _, row in customers_df.iterrows():
        customer_issues = []

        if not is_valid_name(str(row.get("full_name", ""))):
            customer_issues.append("Invalid full name")
        if not is_valid_email(str(row.get("email", ""))):
            customer_issues.append("Invalid email")
        if not is_valid_phone(str(row.get("phone", ""))):
            customer_issues.append("Invalid phone number")

        if customer_issues:
            issues.append((row.to_dict(), customer_issues))

    return issues

# Helper to find duplicated values
def find_duplicates(customers_df, field, min_count=2):
    return customers_df[field].value_counts()[
        customers_df[field].value_counts() >= min_count
    ]

# Address normalization

def normalize_address(addr):
    addr = addr.lower()
    for variant, replacement in ADDRESS_SYNONYMS.items():
        addr = addr.replace(variant, replacement)
    return addr.strip()

# Fraud signal detection
def scan_for_fraud(customers_df):
    fraud_flags = {}

    for field, label, threshold in [
        ("email", "Email reused", 2),
        ("phone", "Phone reused", 2),
        ("address", "Shared address used", 3),
        ("rma_number", "RMA reused", 2)
    ]:
        dupes = find_duplicates(customers_df, field, min_count=threshold)
        for value in dupes.index:
            rows = customers_df[customers_df[field] == value]
            for idx in rows.index:
                if idx not in fraud_flags:
                    fraud_flags[idx] = []
                fraud_flags[idx].append(f"⚠️ {label}: {value}")

    # Check for blacklisted address variants
    blacklisted_norm = [normalize_address(a) for a in ADDRESS_BLACKLIST]
    for idx, row in customers_df.iterrows():
        norm_addr = normalize_address(row.get("address", ""))
        if norm_addr in blacklisted_norm:
            if idx not in fraud_flags:
                fraud_flags[idx] = []
            fraud_flags[idx].append("🚫 Blacklisted address variant")

    return fraud_flags

# Multi-term fuzzy search with scoring
def search_customers(input_value, customers_df, threshold=80, use_fuzzy=True, fields_to_match=None):
    terms = input_value.lower().split()
    matches = []

    for idx, row in customers_df.iterrows():
        matched_fields = set()
        cumulative_score = 0

        for term in terms:
            best_score = 0
            best_field = None

            for field, value in row.items():
                if fields_to_match and field not in fields_to_match:
                    continue
                if pd.isna(value):
                    continue
                value_str = str(value).lower()
                score = fuzz.partial_ratio(term, value_str) if use_fuzzy else int(term in value_str) * 100
                if score > best_score:
                    best_score = score
                    best_field = field

            if best_score >= threshold:
                matched_fields.add(f"{best_field} ({best_score}%)")
                cumulative_score += best_score

        if matched_fields:
            matches.append((idx, row.to_dict(), list(matched_fields), cumulative_score))

    matches.sort(key=lambda x: x[3], reverse=True)
    return matches

# Streamlit UI
customers_df = load_customers("customers.csv")
fraud_flags = scan_for_fraud(customers_df)

query = st.text_input("Enter any identifier (email, phone, ID, name, etc.)")

use_fuzzy = st.checkbox("Use fuzzy matching", value=True)

threshold = st.slider(
    "Fuzzy Match Threshold (%)",
    50, 100, 80,
    help="Higher threshold means stricter match. Lower allows more approximate matches. Only applies if fuzzy matching is enabled."
)

fields = list(customers_df.columns)
fields_to_match = st.multiselect(
    "Select fields to match against (leave empty for all fields)",
    fields,
    default=["full_name", "email", "phone", "address", "customer_id", "member_id", "rma_number", "order_number"]
)

if query:
    results = search_customers(
        query,
        customers_df,
        threshold=threshold,
        use_fuzzy=use_fuzzy,
        fields_to_match=fields_to_match if fields_to_match else None
    )

    if results:
        result_data = []
        fraud_notes = []

        for idx, customer, fields, score in results:
            fraud_note = ", ".join(fraud_flags.get(idx, []))
            fraud_notes.append(fraud_note)
            customer_display = customer.copy()
            customer_display["Match Fields"] = ", ".join(fields)
            customer_display["Score"] = score
            customer_display["Fraud Flags"] = fraud_note
            result_data.append(customer_display)

        styled_df = pd.DataFrame(result_data)

        def highlight_fraud(val):
            return 'background-color: #ffa3a3' if isinstance(val, str) and "⚠️" in val else ''

        st.dataframe(
            styled_df.style.applymap(highlight_fraud, subset=['Fraud Flags'])
        )
    else:
        st.warning("No matches found.")

with st.expander("🧹 View invalid or suspicious entries"):
    bad_entries = find_invalid_entries(customers_df)
    if bad_entries:
        for customer, problems in bad_entries:
            st.markdown("---")
            st.subheader("🚨 Issues: " + ", ".join(problems))
            for k, v in customer.items():
                st.write(f"**{k}**: {v}")
    else:
        st.success("No obvious issues found.")

with st.expander("🔍 View potential fraud signals"):
    if fraud_flags:
        for idx, notes in fraud_flags.items():
            customer = customers_df.loc[idx]
            st.markdown("---")
            st.subheader(", ".join(notes))
            for k, v in customer.items():
                st.write(f"**{k}**: {v}")
    else:
        st.success("No major fraud signals detected.")
