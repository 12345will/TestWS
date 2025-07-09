import streamlit as st
import requests
from textblob import TextBlob
import pandas as pd
from bs4 import BeautifulSoup

SERPAPI_API_KEY = "5cf28550f7b9cb1fb61d5634695e1d8aa7af693b1656602ee95600bdc07ba0ad"

risk_keywords = {
    "labor": {
        "child labor": 3, "forced labor": 3, "unsafe working conditions": 2, "low wages": 1,
        "wage theft": 2, "long hours": 1, "no union": 1, "union suppression": 2,
        "worker abuse": 2, "discrimination": 1, "exploitation": 2, "labor violations": 2,
        "migrant worker abuse": 2, "hazardous working conditions": 2
    },
    "environment": {
        "pollution": 2, "deforestation": 3, "water contamination": 2, "toxic waste": 3,
        "oil spill": 3, "emissions violation": 2, "ecosystem destruction": 3,
        "environmental damage": 2, "climate impact": 2, "greenhouse gas emissions": 2,
        "chemical spill": 2, "air quality issues": 1, "illegal dumping": 2
    },
    "governance": {
        "sanctions": 2, "fraud": 3, "corruption": 3, "bribery": 3, "money laundering": 3,
        "regulatory violation": 2, "fines": 1, "illegal practices": 2, "lack of transparency": 2,
        "anti-competitive behavior": 2, "governance failure": 2, "whistleblower retaliation": 2,
        "non-compliance": 2
    }
}

def search_bhrrc(company_name, max_results=5):
    query = company_name.replace(" ", "+")
    url = f"https://www.business-humanrights.org/en/latest-news/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select(".search-result__title")[:max_results]
        results = []

        for article in articles:
            title = article.get_text(strip=True)
            link = "https://www.business-humanrights.org" + article.find("a")["href"]
            results.append({"title": title, "url": link})
        return results
    except Exception as e:
        return []

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
        "Labor Risk": risk_scores["labor"],
        "Environmental Risk": risk_scores["environment"],
        "Governance Risk": risk_scores["governance"],
        "Sentiment": sentiment,
        "Weighted Risk Score": round(weighted_score, 2),
        "URL": url,
        "Title": title
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

supplier = st.text_input("Enter supplier name:", placeholder="e.g. Glencore")
material = st.text_input("Enter material (e.g., cobalt, lithium):")

st.markdown("### Set Risk Weightings (Total must equal 100%)")
col1, col2, col3 = st.columns(3)
with col1:
    labor_weight = st.slider("Labor Risk %", 0, 100, 40)
with col2:
    env_weight = st.slider("Environmental Risk %", 0, 100, 30)
with col3:
    gov_weight = st.slider("Governance Risk %", 0, 100, 30)

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
            snippet = result.get("snippet", "")
            url = result.get("link", "")
            assessment = assess_article(title, snippet, url, weights)
            articles.append(assessment)

        bhrrc_results = search_bhrrc(supplier)
        bhrrc_count = len(bhrrc_results)
        bhrrc_flag = "✅"
        if bhrrc_count >= 3:
            bhrrc_flag = "🟥"
        elif bhrrc_count >= 1:
            bhrrc_flag = "🟨"

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
- **BHRRC Mentions:** {bhrrc_flag}
""")
            if bhrrc_results:
                st.markdown("**🔗 BHRRC Mentions:**")
                for entry in bhrrc_results:
                    st.markdown(f"- [{entry['title']}]({entry['url']})")
            else:
                st.markdown("**🔗 BHRRC Mentions:** None found")
        else:
            st.warning(f"No articles found for {supplier}.")
