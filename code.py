import streamlit as st
import requests
from textblob import TextBlob
import pandas as pd

# Define your SerpAPI key here
SERPAPI_API_KEY = "5cf28550f7b9cb1fb61d5634695e1d8aa7af693b1656602ee95600bdc07ba0ad"  # Replace with your actual API key

# Risk keywords by category
risk_keywords = {
    "labor": [
        "child labor", "forced labor", "unsafe working conditions", "low wages", "wage theft", "long hours", "no union", "union suppression",
        "worker abuse", "discrimination", "exploitation", "labor violations", "migrant worker abuse", "hazardous working conditions"
    ],
    "environment": [
        "pollution", "deforestation", "water contamination", "toxic waste", "oil spill", "emissions violation", "ecosystem destruction",
        "environmental damage", "climate impact", "greenhouse gas emissions", "chemical spill", "air quality issues", "illegal dumping"
    ],
    "governance": [
        "sanctions", "fraud", "corruption", "bribery", "money laundering", "regulatory violation", "fines", "illegal practices",
        "lack of transparency", "anti-competitive behavior", "governance failure", "whistleblower retaliation", "non-compliance"
    ]
}

def assess_article(title, snippet, weights):
    text = f"{title} {snippet}".lower()
    sentiment = TextBlob(text).sentiment.polarity

    risk_counts = {k: 0 for k in risk_keywords}
    for category, keywords in risk_keywords.items():
        for kw in keywords:
            if kw in text:
                risk_counts[category] += 1

    weighted_score = (
        risk_counts["labor"] * weights["labor"] +
        risk_counts["environment"] * weights["environment"] +
        risk_counts["governance"] * weights["governance"]
    ) / 100

    return {
        "Title": title,
        "Labor Risk": risk_counts["labor"],
        "Environmental Risk": risk_counts["environment"],
        "Governance Risk": risk_counts["governance"],
        "Sentiment": sentiment,
        "Weighted Risk Score": weighted_score
    }

def search_articles(query):
    params = {
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "engine": "google",
        "num": 10
    }
    response = requests.get("https://serpapi.com/search", params=params)
    return response.json().get("organic_results", [])

st.set_page_config(page_title="Supplier Risk Assessment Tool", layout="wide")
st.title("🔍 Supplier Risk Assessment Tool")
st.markdown("This tool lets you assess reputational risk of suppliers based on online news sources.")

company = st.text_input("Enter Supplier/Company Name", placeholder="e.g., Glencore")
material = st.text_input("Enter Material/Commodity", placeholder="e.g., cobalt")

st.markdown("### Set Risk Weightings (Total must equal 100%)")
col1, col2, col3 = st.columns(3)
with col1:
    labor_weight = st.slider("Labor Risk %", 0, 100, 40)
with col2:
    env_weight = st.slider("Environmental Risk %", 0, 100, 30)
with col3:
    gov_weight = st.slider("Governance Risk %", 0, 100, 30)

if labor_weight + env_weight + gov_weight != 100:
    st.warning("⚠️ The weights must add up to 100%.")
else:
    if st.button("Run Risk Assessment"):
        if not company or not material:
            st.error("Please enter both a company and material.")
        else:
            query = f"{company} {material} ESG human rights labor pollution"
            st.write(f"Searching for: `{query}`")

            results = search_articles(query)
            weights = {
                "labor": labor_weight,
                "environment": env_weight,
                "governance": gov_weight
            }

            data = []
            for result in results:
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                url = result.get("link", "")
                analysis = assess_article(title, snippet, weights)
                analysis["URL"] = url
                data.append(analysis)

            if data:
                df = pd.DataFrame(data)
                st.markdown("### 🧾 Results")
                st.dataframe(df.sort_values(by="Weighted Risk Score", ascending=False), use_container_width=True)
            else:
                st.info("No relevant articles found. Try adjusting the company or material.")
