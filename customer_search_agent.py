import csv
import re

# Load customer data from CSV
def load_customers(file_path):
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

# Classify input to give hints (optional step)
def classify_input(value):
    if re.match(r"[^@]+@[^@]+\.[^@]+", value):
        return "email"
    elif re.match(r"^\+?\d{7,15}$", value):
        return "phone"
    elif value.isdigit():
        return "numeric"
    elif re.match(r"[A-Za-z]+(?:\s+[A-Za-z]+)+", value):
        return "name"
    else:
        return "ambiguous"

# Search all fields for a match
def search_customers(input_value, customers):
    input_value_lower = input_value.lower()
    matches = []

    for customer in customers:
        matched_fields = []
        for field, value in customer.items():
            if input_value_lower in str(value).lower():
                matched_fields.append(field)
        if matched_fields:
            matches.append({
                "customer": customer,
                "matched_fields": matched_fields
            })

    return matches

# Format the result
def print_matches(matches):
    if not matches:
        print("No matches found.")
    for match in matches:
        customer = match["customer"]
        fields = ", ".join(match["matched_fields"])
        print(f"\n🎯 Match found in: {fields}")
        for k, v in customer.items():
            print(f"  {k}: {v}")

# Sample usage
if __name__ == "__main__":
    # Replace with your own path if needed
    sample_file = "customers.csv"

    print("🔎 AI Customer Search Agent")
    customers = load_customers(sample_file)

    while True:
        query = input("\nEnter a search value (or 'exit'): ").strip()
        if query.lower() == "exit":
            break
        matches = search_customers(query, customers)
        print_matches(matches)
