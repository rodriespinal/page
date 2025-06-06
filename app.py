import streamlit as st
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import google.generativeai as genai
import json
import pandas as pd

# === CONFIGURATION ===
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# === FUNCTIONS ===

def reverse_geocode_osm(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {'lat': lat, 'lon': lon, 'format': 'json', 'addressdetails': 1}
    headers = {'User-Agent': 'TownhouseFinderApp/1.0 (your_email@example.com)'}
    res = requests.get(url, params=params, headers=headers)
    return res.json().get("display_name") if res.status_code == 200 else None

def get_google_links(query, num_results=10):
    return list(search(query, num_results=num_results))

def scrape_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        html = requests.get(url, headers=headers, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator=' ', strip=True)[:10000]
    except Exception as e:
        return f"Error scraping {url}: {e}"

def extract_info_with_gemini(text):
    model = genai.GenerativeModel("gemini-pro")
    prompt = f"""
You are an assistant extracting townhouse complex data from real estate-related text.

Given this page content, extract:
- Complex name
- Strata corporation number
- Number of units or suites
- Number of levels (floors)

Text:
\"\"\"
{text}
\"\"\"

Return a JSON object. Use null for any unknown field.
"""
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini error: {e}")
        return {}

# === STREAMLIT UI ===

st.set_page_config(page_title="Townhouse Info Finder", page_icon="🏘️")
st.title("🏘️ Townhouse Info Finder (Gemini Edition)")

lat = st.number_input("Latitude", format="%.6f")
lon = st.number_input("Longitude", format="%.6f")

if st.button("Find Townhouse Info"):
    with st.spinner("🔍 Reverse geocoding coordinates..."):
        address = reverse_geocode_osm(lat, lon)
    if not address:
        st.error("Failed to reverse geocode address.")
        st.stop()
    st.success(f"Address: {address}")

    with st.spinner("🧠 Searching Google..."):
        links = get_google_links(address)
    st.write("🔗 Top Google Results:")
    for link in links:
        st.markdown(f"- [{link}]({link})")

    all_data = []
    with st.spinner("⏳ Scraping & analyzing pages..."):
        for link in links:
            text = scrape_text(link)
            result = extract_info_with_gemini(text)
            if result:
                result["source"] = link
                all_data.append(result)

    if all_data:
        df = pd.DataFrame(all_data)
        st.success("✅ Info extracted!")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv, "townhouse_info.csv", "text/csv")
    else:
        st.warning("❌ No data could be extracted from search results.")
