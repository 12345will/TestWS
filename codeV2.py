import streamlit as st
import requests
from textblob import TextBlob
import pandas as pd
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


# --- Risk Keywords ---
risk_keywords = {
    "labor": {
        "child labor": 3, "forced labor": 3, "bonded labor": 3, "modern slavery": 3,
        "human trafficking": 3, "unsafe working conditions": 2, "low wages": 1,
        "wage theft": 2, "long working hours": 1, "long hours": 1,
        "no union": 1, "union suppression": 2, "anti-union practices": 2,
        "worker abuse": 2, "discrimination": 1, "gender-based violence": 2,
        "sexual harassment": 2, "exploitation": 2, "labor violations": 2,
        "migrant worker abuse": 2, "hazardous working conditions": 2,
        "worker deaths": 3, "occupational hazard": 2, "factory collapse": 3,
        "temporary contracts": 1, "unpaid overtime": 2, "lack of health insurance": 1,
        "retaliation": 2
    },
    "environment": {
        "pollution": 2, "air pollution": 2, "water pollution": 2, "soil contamination": 2,
        "deforestation": 3, "biodiversity loss": 3, "habitat destruction": 3,
        "water contamination": 2, "toxic waste": 3, "oil spill": 3, "chemical spill": 2,
        "emissions violation": 2, "illegal logging": 3, "ecosystem destruction": 3,
        "environmental damage": 2, "climate impact": 2, "greenhouse gas emissions": 2,
        "carbon emissions": 2, "methane emissions": 2, "illegal dumping": 2,
        "waste mismanagement": 1, "overconsumption": 1, "excessive packaging": 1,
        "resource depletion": 2, "water overuse": 2, "tailings dam": 3,
        "dam collapse": 3, "brumadinho": 3, "toxic sludge": 3,
        "mining disaster": 3, "environmental catastrophe": 3, "negative impact": 3
    },
    "governance": {
        "sanctions": 2, "fraud": 3, "accounting fraud": 3, "corruption": 3,
        "bribery": 3, "embezzlement": 3, "money laundering": 3,
        "regulatory violation": 2, "fines": 1, "illegal practices": 2,
        "lack of transparency": 2, "governance failure": 2,
        "whistleblower retaliation": 2, "non-compliance": 2,
        "anti-competitive behavior": 2, "insider trading": 2,
        "misleading reporting": 2, "data breach": 2, "privacy violation": 2,
        "cybersecurity failure": 2, "board conflicts of interest": 2,
        "lawsuit": 2, "settlement": 2, "criminal charges": 3,
        "investigation": 2, "stock manipulation": 3
    }
}



# --- Diffbot Article Extractor ---
def get_full_text(url):
    try:
        DIFFBOT_TOKEN = "070489d54ba6e1dbb01ff6c8ca766530"
        api_url = f"https://api.diffbot.com/v3/article?token={DIFFBOT_TOKEN}&url={url}"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "objects" in data and len(data["objects"]) > 0:
            return data["objects"][0].get("text", "")
        return ""
    except Exception as e:
        return f"[Error extracting article text: {e}]"

# --- Risk Assessment Function ---
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
        "Labor Risk": risk_scores["labor"],
        "Environmental Risk": risk_scores["environment"],
        "Governance Risk": risk_scores["governance"],
        "Sentiment": sentiment,
        "Weighted Risk Score": round(weighted_score, 2),
        "URL": url,
        "Title": title
    }

# --- Google Programmable Search API ---
GOOGLE_API_KEY = "AIzaSyCEWC7rZUu8EDPFeVtNsWrsdBv0HVcJ_dg"
CSE_ID = "57a79da21c554499f"

def search_articles(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": CSE_ID,
        "q": query,
        "num": 10
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return [{
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet", "")
        } for item in data.get("items", [])]
    except Exception as e:
        print("Error fetching search results:", e)
        return []

# --- Streamlit App UI ---
st.set_page_config(page_title="Supplier Risk Assessment Tool", layout="wide")
st.title("🔍 Supplier Risk Assessment Tool")

supplier = st.text_input("Enter supplier name:", placeholder="e.g. Glencore")
material = st.text_input("Enter material (e.g., cobalt, lithium):")

st.markdown("### Set Risk Weightings (Total must equal 100%)")
col1, col2, col3 = st.columns(3)
with col1:
    labor_weight = st.slider("Labor Risk %", 0, 100, 40, step=5)
with col2:
    env_weight = st.slider("Environmental Risk %", 0, 100, 30, step=5)
with col3:
    gov_weight = st.slider("Governance Risk %", 0, 100, 30, step=5)

if labor_weight + env_weight + gov_weight != 100:
    st.warning("⚠️ Weights must total 100%.")
elif st.button("Run Risk Assessment"):
    if not supplier or not material:
        st.error("Please enter a supplier and a material.")
    else:
        weights = {
            "labor": labor_weight,
            "environment": env_weight,
            "governance": gov_weight
        }

        st.markdown(f"#### 🔎 Searching for: {supplier}")
        query = f"{supplier} {material} ESG human rights labor environment governance"
        results = search_articles(query)
        articles = []

        for result in results:
            title = result.get("title", "")
            url = result.get("link", "")
            snippet = result.get("snippet", "")
            assessment = assess_article(title, snippet, url, weights)
            if assessment["Weighted Risk Score"] > 0:
                articles.append(assessment)


        if articles:
            df = pd.DataFrame(articles)
            st.markdown("### 📰 Assessed Articles")
            st.dataframe(df.sort_values(by="Weighted Risk Score", ascending=False))

            avg_risk = round(df["Weighted Risk Score"].mean(), 2)
            interpret = lambda score: "✅" if score <= 5.5 else "⚠️" if score <= 7 else "❌"

            st.markdown(f"""
### 🧾 Final Risk Summary for **{supplier}**
- **Labor Risk (avg):** {round(df["Labor Risk"].mean(), 2)} / 10  
- **Environmental Risk (avg):** {round(df["Environmental Risk"].mean(), 2)} / 10  
- **Governance Risk (avg):** {round(df["Governance Risk"].mean(), 2)} / 10  
- **→ Total Weighted Risk Score:** **{avg_risk} / 10** {interpret(avg_risk)}
""")
        else:
            st.warning(f"No articles found for {supplier}.")
