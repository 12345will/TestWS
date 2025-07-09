import streamlit as st
import requests
from textblob import TextBlob
import pandas as pd
import spacy
import setup


# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# --- ESG Risk Keywords ---
risk_keywords = {
    "labor": {
        "child labor": 3, "forced labor": 3, "bonded labor": 3, "modern slavery": 3,
        "human trafficking": 3, "unsafe working conditions": 2, "low wages": 1,
        "wage theft": 2, "long working hours": 1, "no union": 1,
        "union suppression": 2, "worker abuse": 2, "discrimination": 1,
        "gender-based violence": 2, "sexual harassment": 2, "exploitation": 2,
        "labor violations": 2, "migrant worker abuse": 2, "hazardous working conditions": 2,
        "worker deaths": 3, "factory collapse": 3, "unpaid overtime": 2
    },
    "environment": {
        "pollution": 2, "deforestation": 3, "biodiversity loss": 3, "habitat destruction": 3,
        "toxic waste": 3, "chemical spill": 2, "oil spill": 3, "greenhouse gas emissions": 2,
        "carbon emissions": 2, "illegal dumping": 2, "tailings dam": 3,
        "mining disaster": 3, "climate impact": 2, "resource depletion": 2
    },
    "governance": {
        "sanctions": 2, "fraud": 3, "corruption": 3, "bribery": 3,
        "money laundering": 3, "non-compliance": 2, "whistleblower retaliation": 2,
        "anti-competitive behavior": 2, "data breach": 2, "lawsuit": 2,
        "criminal charges": 3, "governance failure": 2
    }
}

# --- Diffbot Article Extractor ---
def get_full_text(url):
    try:
        token = "070489d54ba6e1dbb01ff6c8ca766530"
        api_url = f"https://api.diffbot.com/v3/article?token={token}&url={url}"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "objects" in data and len(data["objects"]) > 0:
            return data["objects"][0].get("text", "")
        return ""
    except Exception as e:
        return f"[Error extracting article text: {e}]"

# --- ESG Risk Assessment ---
def assess_article(title, snippet, url, full_text, weights):
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

# --- Extract Suppliers from Text ---
def extract_suppliers(text):
    doc = nlp(text)
    orgs = [ent.text.strip() for ent in doc.ents if ent.label_ == "ORG"]
    return list(set(orgs))  # Remove duplicates

# --- Google Custom Search API ---
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

# --- Streamlit UI ---
st.set_page_config(page_title="Material-Based Supplier Risk Tool", layout="wide")
st.title("🔎 Material-Based Supplier Risk Tool")

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
elif st.button("Find Best Supplier"):
    if not material:
        st.error("Please enter a material.")
    else:
        weights = {"labor": labor_weight, "environment": env_weight, "governance": gov_weight}
        query = f"{material} ESG mining supplier human rights environment governance"
        search_results = search_articles(query)

        supplier_scores = {}
        article_count = 0

        for result in search_results:
            title = result.get("title", "")
            url = result.get("link", "")
            snippet = result.get("snippet", "")
            full_text = get_full_text(url)
            combined = f"{title} {snippet} {full_text}"
            mentioned_suppliers = extract_suppliers(combined)

            if not mentioned_suppliers:
                continue

            assessment = assess_article(title, snippet, url, full_text, weights)
            article_count += 1
            for supplier in mentioned_suppliers:
                supplier_scores.setdefault(supplier, []).append(assessment)

        if not supplier_scores:
            st.warning(f"No suppliers identified in the articles for '{material}'.")
        else:
            summary = []
            for supplier, assessments in supplier_scores.items():
                avg_score = round(sum(a["Weighted Risk Score"] for a in assessments) / len(assessments), 2)
                summary.append({
                    "Supplier": supplier,
                    "Average Risk Score": avg_score,
                    "Articles Found": len(assessments)
                })

            df_summary = pd.DataFrame(summary).sort_values("Average Risk Score")
            st.markdown("### 🧾 Supplier Risk Summary")
            st.dataframe(df_summary)

            top_supplier = df_summary.iloc[0]
            st.markdown(f"""
### 🥇 Recommended Supplier for **{material}**: **{top_supplier["Supplier"]}**
- **Avg Risk Score:** {top_supplier["Average Risk Score"]} / 10
- **Articles Assessed:** {top_supplier["Articles Found"]}
""")
