import streamlit as st
import requests
from textblob import TextBlob
import pandas as pd
from bs4 import BeautifulSoup

# Access SerpAPI key from Streamlit secrets
SERPAPI_API_KEY = st.secrets["5cf28550f7b9cb1fb61d5634695e1d8aa7af693b1656602ee95600bdc07ba0ad"]

# Risk keywords with severity weights
risk_keywords = {
    "labor": {
        "child labor": 3,
        "forced labor": 3,
        "unsafe working conditions": 2,
        "low wages": 1,
        "wage theft": 2,
        "long hours": 1,
        "no union": 1,
        "union suppression": 2,
        "worker abuse": 2,
        "discrimination": 1,
        "exploitation": 2,
        "labor violations": 2,
        "migrant worker abuse": 2,
        "hazardous working conditions": 2
    },
    "environment": {
        "pollution": 2,
        "deforestation": 3,
        "water contamination": 2,
        "toxic waste": 3,
        "oil spill": 3,
        "emissions violation": 2,
        "ecosystem destruction": 3,
        "environmental damage": 2,
        "climate impact": 2,
        "greenhouse gas emissions": 2,
        "chemical spill": 2,
        "air quality issues": 1,
        "illegal dumping": 2
    },
    "governance": {
        "sanctions": 2,
        "fraud": 3,
        "corruption": 3,
        "bribery": 3,
        "money laundering": 3,
        "regulatory violation": 2,
        "fines": 1,
        "illegal practices": 2,
        "lack of transparency": 2,
        "anti-competitive behavior": 2,
        "governance failure": 2,
        "whistleblower retaliation": 2,
        "non-compliance": 2
    }
}

def get_full_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs])
        return text
    except:
        return ""

def assess_article(title, snippet, url, weights):
    full_text = get_full_text(url)
    combined_text = f"{title} {snippet} {full_text}".lower()
    sentiment = TextBlob(combined_text).sentiment.polarity

    risk_scores = {k: 0 for k in risk_keywords}
    for category, terms in risk_keywords.items():
        for kw, severity in terms.items():
            if kw in combined_text:
                risk_scores[category] += severity

    weighted_score = (
        risk_scores["labor"] * weights["labor"] +
        risk_scores["environment"] * weights["environment"] +
        risk_scores["governance"] * weights["governance"]
    ) / 100

    return {
        "Title": title,
        "Labor Risk": risk_scores["labor"],
        "Environmental Risk": risk_scores["environment"],
        "Governance Risk": risk_scores["governance"],
        "Sentiment": sentiment,
        "Weighted Risk Score": weighted_score,
        "URL": url
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
st.markdown("This tool assesses reputational risk of suppliers by analyzing full article content.")

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
                analysis = assess_article(title, snippet, url, weights)
                data.append(analysis)

            if data:
                df = pd.DataFrame(data)
                st.markdown("### 🧾 Results")
                st.dataframe(df.sort_values(by="Weighted Risk Score", ascending=False), use_container_width=True)
            else:
                st.info("No relevant articles found. Try adjusting the company or material.")
