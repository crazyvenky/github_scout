import streamlit as st
import requests

def get_repos(language="python", sort_by="stars", order="desc", per_page=5):
    url = "https://api.github.com/search/repositories"
    params = {
        "q": f"language:{language}",
        "sort": sort_by,
        "order": order,
        "per_page": per_page
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()["items"]

st.title("GitHub Trending Repositories")

language = st.selectbox("Language", ["python", "javascript", "java", "go", "c++", "ruby"])
sort_by = st.selectbox("Sort by", ["stars", "forks", "updated"])
order = st.selectbox("Order", ["desc", "asc"])
per_page = st.slider("Number of repositories", 1, 20, 5)

if st.button("Get Repositories"):
    repos = get_repos(language, sort_by, order, per_page)
    for repo in repos:
        st.markdown(f"[{repo['name']}]({repo['html_url']}) - ⭐ {repo['stargazers_count']} | 🍴 {repo['forks_count']}")