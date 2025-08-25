import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
import json
import os
from dataclasses import dataclass
import google.generativeai as genai

# Configuration
GITHUB_API_BASE = "https://api.github.com"
MAJOR_COMPANIES = ['google', 'microsoft', 'facebook', 'amazon', 'apple', 'netflix', 'uber', 'twitter']

@dataclass
class RepoData:
    name: str
    full_name: str
    stars: int
    forks: int
    language: str
    description: str
    url: str
    created_at: str
    updated_at: str
    topics: List[str]
    has_wiki: bool
    open_issues: int
    score: float = 0.0
    reasoning: str = ""

class GitHubTrendingScanner:
    def __init__(self, github_token=None):
        self.token = github_token
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        
        if github_token and github_token.strip():
            self.headers['Authorization'] = f'token {github_token.strip()}'
        
        self.rate_limit_remaining = 60
    
    def check_rate_limit(self):
        """Check GitHub API rate limit status"""
        try:
            response = requests.get(f"{GITHUB_API_BASE}/rate_limit", headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                self.rate_limit_remaining = data['rate']['remaining']
                return True, data
            else:
                return False, f"Rate limit check failed: {response.status_code}"
        except Exception as e:
            return False, f"Could not check rate limit: {e}"
    
    def search_repositories(self, query: str, sort: str = "stars", per_page: int = 30) -> List[Dict]:
        """Search GitHub repositories with given query"""
        if self.rate_limit_remaining <= 5:
            st.warning("⚠️ GitHub API rate limit low. Consider adding a GitHub token.")
            return []
        
        url = f"{GITHUB_API_BASE}/search/repositories"
        params = {
            'q': query,
            'sort': sort,
            'order': 'desc',
            'per_page': per_page
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                self.rate_limit_remaining -= 1
                data = response.json()
                return data.get('items', [])
            elif response.status_code == 403:
                st.error("🚫 GitHub API rate limit exceeded. Please add a GitHub token or try again later.")
                return []
            elif response.status_code == 422:
                st.error(f"🔍 Invalid search query: {query}")
                return []
            else:
                st.error(f"GitHub API error: {response.status_code} - {response.text[:200]}")
                return []
                
        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out. GitHub API might be slow.")
            return []
        except Exception as e:
            st.error(f"Error fetching repositories: {str(e)}")
            return []
    
    def get_repository_details(self, owner: str, repo: str) -> Dict:
        """Get detailed information about a specific repository"""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                st.warning(f"Could not fetch details for {owner}/{repo}: {response.status_code}")
        except Exception as e:
            st.error(f"Error fetching repo details: {e}")
        return {}
    
    def calculate_interest_score(self, repo: Dict) -> Dict:
        """Calculate interest score for a repository"""
        base_popularity = (
            repo.get('stargazers_count', 0) * 1.0 +
            repo.get('forks_count', 0) * 2.0 +
            repo.get('watchers_count', 0) * 1.5
        )
        
        try:
            created_date = datetime.strptime(repo['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            days_old = (datetime.now() - created_date).days
            recency_multiplier = max(0.1, 1.0 - (days_old / 365))
        except:
            recency_multiplier = 0.5
        
        activity_score = (
            repo.get('open_issues_count', 0) * 0.1 +
            (10 if repo.get('has_wiki', False) else 0) +
            len(repo.get('topics', [])) * 5
        )
        
        language_multipliers = {
            'JavaScript': 1.2, 'Python': 1.3, 'TypeScript': 1.1,
            'Go': 1.0, 'Rust': 1.4, 'Swift': 0.9, 'Kotlin': 0.8,
            'Java': 1.1, 'C++': 1.0, 'C#': 0.9, 'PHP': 0.8
        }
        language_boost = language_multipliers.get(repo.get('language'), 1.0)
        
        final_score = (base_popularity + activity_score) * recency_multiplier * language_boost
        
        reasoning = f"Pop: {base_popularity:.1f}, Activity: {activity_score:.1f}, Recency: {recency_multiplier:.2f}, Lang: {language_boost:.1f}"
        
        return {
            'repo': repo,
            'score': final_score,
            'reasoning': reasoning
        }
    
    def scan_trending_by_category(self, category: str, days_back: int = 7) -> List[Dict]:
        """Scan trending repositories by different categories"""
        date_threshold = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        queries = {
            'newly_created': f'created:>{date_threshold}',
            'recently_active': f'pushed:>{date_threshold} stars:>10',
            'hot_topics': f'good-first-issues:>0 created:>{date_threshold}',
            'ai_ml_trending': f'topic:machine-learning created:>{date_threshold}',
            'web_dev_trending': f'topic:react created:>{date_threshold}',
            'devops_trending': f'topic:docker created:>{date_threshold}',
            'mobile_trending': f'topic:android created:>{date_threshold}',
            'breaking_out': f'stars:100..1000 created:>{date_threshold}',
            'hidden_gems': f'stars:10..100 forks:>5 created:>{date_threshold}'
        }
        
        if category not in queries:
            st.error(f"Unknown category: {category}")
            return []
        
        repos = self.search_repositories(queries[category])
        scored_repos = []
        
        for repo in repos:
            scored_repo = self.calculate_interest_score(repo)
            scored_repos.append(scored_repo)
        
        return sorted(scored_repos, key=lambda x: x['score'], reverse=True)

class GeminiAnalyzer:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.model = None
        
        if api_key and api_key.strip():
            try:
                genai.configure(api_key=api_key.strip())
                # FIXED: Use the correct model name
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                st.error(f"Failed to initialize Gemini: {e}")
                self.model = None
    
    def test_connection(self):
        """Test Gemini API connection"""
        if not self.api_key or not self.model:
            return False, "No API key provided"
        
        try:
            # Test with a simple prompt
            response = self.model.generate_content("Hello, this is a connection test.")
            if response.text:
                return True, "Connected successfully"
            else:
                return False, "No response received"
        except Exception as e:
            # Try alternative model names if the first one fails
            try:
                self.model = genai.GenerativeModel('gemini-pro')
                response = self.model.generate_content("Hello, test connection.")
                return True, "Connected successfully"
            except:
                try:
                    self.model = genai.GenerativeModel('gemini-1.5-pro')
                    response = self.model.generate_content("Hello, test connection.")
                    return True, "Connected successfully"
                except:
                    return False, f"Connection failed: {str(e)}"
    
    def analyze_repository(self, repo_url: str, repo_data: dict) -> str:
        """Analyze repository using Gemini API and return structured notes for NotebookLM"""
        if not self.model:
            return "⚠️ Gemini API key not configured. Please add your API key in the sidebar."
        
        prompt = f"""
Please analyze this GitHub repository and create comprehensive, structured notes suitable for NotebookLM podcast generation:

Repository URL: {repo_url}
Repository Name: {repo_data.get('full_name', 'Unknown')}
Description: {repo_data.get('description', 'No description available')}
Language: {repo_data.get('language', 'Unknown')}
Stars: {repo_data.get('stargazers_count', 0):,}
Forks: {repo_data.get('forks_count', 0):,}
Created: {repo_data.get('created_at', 'Unknown')[:10]}
Topics: {', '.join(repo_data.get('topics', []))}

Please provide detailed analysis covering:

## 1. Repository Overview
- What problem does this repository solve?
- Who is the target audience?
- What makes it unique or special?

## 2. Technical Analysis  
- Key technologies and frameworks used
- Architecture and design patterns
- Code quality indicators
- Dependencies and ecosystem

## 3. Community & Adoption
- Developer community engagement
- Real-world usage examples
- Notable contributors or organizations
- Recent development activity

## 4. Content Opportunities
- Why is this repository trending/interesting now?
- What story angles could work for video content?
- Key talking points for developers
- Potential controversies or interesting decisions

## 5. Comparison & Context
- How does it compare to alternatives?
- Where does it fit in the ecosystem?
- Evolution and future roadmap

## 6. Practical Insights
- Getting started guide summary
- Common use cases
- Performance characteristics
- Learning curve and documentation quality

Format the response as detailed, podcast-friendly notes that can be fed into NotebookLM for audio generation. Include specific examples, statistics, and technical details that would make for engaging content.
"""

        try:
            with st.spinner("🤖 Analyzing repository with Gemini AI..."):
                response = self.model.generate_content(prompt)
                return response.text if response.text else "❌ No response generated"
        except Exception as e:
            return f"❌ Error analyzing repository: {str(e)}"

def show_repo_details_modal(repo, key_suffix="", gemini_analyzer=None):
    """Show repository details in an expandable format"""
    with st.expander(f"📊 {repo['full_name']} Details", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**Description:** {repo.get('description', 'No description')}")
            st.write(f"**Language:** {repo.get('language', 'Unknown')}")
            st.write(f"**Topics:** {', '.join(repo.get('topics', []))}")
            st.write(f"**Created:** {repo['created_at'][:10]}")
            st.write(f"**Last Updated:** {repo['updated_at'][:10]}")
            st.write(f"**Repository URL:** {repo['html_url']}")
        
        with col2:
            st.metric("⭐ Stars", f"{repo['stargazers_count']:,}")
            st.metric("🍴 Forks", f"{repo['forks_count']:,}")
            st.metric("👀 Watchers", f"{repo['watchers_count']:,}")
        
        with col3:
            st.metric("🐛 Issues", repo['open_issues_count'])
            st.metric("📚 Wiki", "Yes" if repo.get('has_wiki') else "No")
            st.metric("📄 License", repo.get('license', {}).get('name', 'Unknown') if repo.get('license') else 'None')
            
        # Video generation button with Gemini integration
        if st.button(f"🎬 Generate Video Content with AI Analysis", key=f"video_{key_suffix}"):
            generate_video_content_with_ai(repo, gemini_analyzer)

def generate_video_content_with_ai(repo, gemini_analyzer):
    """Generate video content with AI analysis from Gemini"""
    st.success(f"🎬 Generating AI-powered video content for {repo['full_name']}...")
    
    # Get AI analysis
    if gemini_analyzer and gemini_analyzer.model:
        ai_analysis = gemini_analyzer.analyze_repository(repo['html_url'], repo)
    else:
        ai_analysis = "⚠️ Gemini API not configured. Using basic template."
    
    # Content analysis
    content_type = determine_content_type(repo)
    script_template = generate_script_template(repo, content_type)
    
    st.subheader("🤖 AI-Generated Repository Analysis")
    st.markdown(ai_analysis)
    
    st.subheader("📝 NotebookLM Ready Content")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 Content Strategy")
        st.write(f"**Content Type:** {content_type}")
        st.write(f"**Estimated Video Length:** 8-12 minutes")
        st.write(f"**Target Audience:** {get_target_audience(repo)}")
        st.write(f"**Best Upload Time:** {get_optimal_upload_time(repo)}")
        
        st.markdown("### 📊 Key Metrics to Highlight")
        st.write(f"• ⭐ {repo['stargazers_count']:,} stars")
        st.write(f"• 🍴 {repo['forks_count']:,} forks") 
        st.write(f"• 📅 Created {repo['created_at'][:10]}")
        st.write(f"• 🏷️ Main language: {repo.get('language', 'Unknown')}")
    
    with col2:
        st.markdown("### 🎬 Video Title Ideas")
        titles = generate_video_titles(repo)
        for i, title in enumerate(titles, 1):
            st.write(f"{i}. {title}")
        
        st.markdown("### 🏷️ Suggested Tags")
        tags = generate_video_tags(repo)
        st.write(", ".join(tags))
    
    # Save analysis for NotebookLM
    notebook_content = f"""
# Repository Analysis: {repo['full_name']}

{ai_analysis}

## Video Production Notes
- **Content Type:** {content_type}
- **Target Audience:** {get_target_audience(repo)}
- **Key Metrics:** {repo['stargazers_count']:,} stars, {repo['forks_count']:,} forks
- **Repository URL:** {repo['html_url']}
- **Main Language:** {repo.get('language', 'Unknown')}
- **Created:** {repo['created_at'][:10]}

## Suggested Video Titles
{chr(10).join([f"- {title}" for title in titles])}

## Video Tags
{', '.join(tags)}

---
*Generated by GitHub Trending Scout with Gemini AI Analysis*
    """
    
    st.download_button(
        label="📚 Download NotebookLM Content",
        data=notebook_content,
        file_name=f"{repo['name']}_analysis.md",
        mime="text/markdown",
        help="Download this analysis to upload to NotebookLM for podcast generation"
    )
    
    # Save to session state
    st.session_state[f'ai_analysis_{repo["id"]}'] = {
        'repo': repo,
        'analysis': ai_analysis,
        'content_type': content_type,
        'titles': titles,
        'tags': tags,
        'notebook_content': notebook_content
    }

def determine_content_type(repo):
    """Determine the best content type based on repository characteristics"""
    stars = repo['stargazers_count']
    age_days = (datetime.now() - datetime.strptime(repo['created_at'], '%Y-%m-%dT%H:%M:%SZ')).days
    
    if stars > 10000:
        return "🌟 Popular Repository Spotlight"
    elif age_days < 30 and stars > 100:
        return "🚀 Rising Star Analysis"
    elif stars < 1000 and repo.get('forks_count', 0) > 50:
        return "💎 Hidden Gem Discovery"
    elif 'ai' in repo.get('description', '').lower() or 'machine-learning' in repo.get('topics', []):
        return "🤖 AI Tool Review"
    else:
        return "🔍 Repository Deep Dive"

def generate_video_titles(repo):
    """Generate engaging video titles"""
    stars = repo['stargazers_count']
    name = repo['name']
    
    titles = [
        f"This {repo.get('language', 'GitHub')} Repository Has {stars:,} Stars - Here's Why",
        f"{name}: The Tool Every Developer Needs to Know About",
        f"I Found This Amazing {repo.get('language', 'GitHub')} Project With {stars:,} Stars",
        f"Why {name} is Trending on GitHub Right Now",
        f"{name} Review: Worth the Hype? ({stars:,} Stars)"
    ]
    return titles

def generate_video_tags(repo):
    """Generate relevant video tags"""
    base_tags = ["github", "programming", "coding", "opensource", "developer"]
    
    if repo.get('language'):
        base_tags.append(repo['language'].lower())
    
    for topic in repo.get('topics', [])[:5]:
        base_tags.append(topic)
    
    return base_tags

def generate_script_template(repo, content_type):
    """Generate a video script template"""
    return f"""
# {content_type}: {repo['full_name']}

## Hook (0-15 seconds)
"This repository just hit {repo['stargazers_count']:,} stars, and I can see why. Let me show you what makes {repo['name']} special."

## Problem Setup (15-45 seconds)  
"If you've ever worked with {repo.get('language', 'this technology')}, you know that [INSERT COMMON PROBLEM]. Well, {repo['name']} might be exactly what you've been looking for."

## Repository Overview (45-120 seconds)
- **What it does:** {repo.get('description', 'Add description here')}
- **Main language:** {repo.get('language', 'Unknown')}
- **Created:** {repo['created_at'][:10]}
- **Key features:** [Research and add 3-5 key features]

## Demo/Code Examples (120-300 seconds)
"Let me show you how this works in practice..."
[INSERT CODE EXAMPLES AND DEMOS]

## Community & Adoption (300-360 seconds)
- **Community stats:** {repo['stargazers_count']:,} stars, {repo['forks_count']:,} forks
- **Contributors:** {repo.get('contributors', 'Multiple')} developers
- **Use cases:** [Research real-world usage]
- **Companies using it:** [Research if any known companies use it]

## Comparison (360-400 seconds)
"How does this compare to alternatives like [INSERT ALTERNATIVES]?"

## Call to Action (400-420 seconds)
"What do you think about {repo['name']}? Have you used it in your projects? Let me know in the comments below!"

---
## Research Notes:
- Repository URL: {repo['html_url']}
- Documentation: [Check README and docs]
- Recent updates: {repo['updated_at'][:10]}
- License: {repo.get('license', {}).get('name', 'Check license')}
"""

def get_target_audience(repo):
    """Determine target audience based on repository"""
    language = repo.get('language', '').lower()
    topics = [topic.lower() for topic in repo.get('topics', [])]
    
    if 'machine-learning' in topics or 'ai' in topics:
        return "AI/ML Engineers, Data Scientists"
    elif language in ['javascript', 'typescript', 'react']:
        return "Frontend Developers, Full-stack Engineers"
    elif language in ['python']:
        return "Python Developers, Backend Engineers"
    elif 'devops' in topics or language in ['dockerfile', 'kubernetes']:
        return "DevOps Engineers, System Administrators"
    else:
        return "General Developers, Programming Enthusiasts"

def get_optimal_upload_time(repo):
    """Suggest optimal upload time based on repository type"""
    topics = [topic.lower() for topic in repo.get('topics', [])]
    
    if any(topic in ['ai', 'machine-learning', 'data-science'] for topic in topics):
        return "Tuesday 10 AM PST (high engagement from tech professionals)"
    elif any(topic in ['web', 'frontend', 'react', 'javascript'] for topic in topics):
        return "Wednesday 9 AM PST (web developers active)"
    else:
        return "Tuesday-Thursday 9-11 AM PST (general developer audience)"

def test_api_connections(github_scanner, gemini_analyzer):
    """Test both GitHub and Gemini API connections"""
    st.subheader("🧪 API Connection Test")
    
    if st.button("🔍 Test All Connections"):
        results = []
        
        # Test GitHub API
        github_status, github_msg = github_scanner.check_rate_limit()
        if github_status:
            results.append("✅ GitHub API: Connection stable")
        else:
            results.append(f"❌ GitHub API: {github_msg}")
        
        # Test Gemini API
        if gemini_analyzer.api_key:
            gemini_status, gemini_msg = gemini_analyzer.test_connection()
            if gemini_status:
                results.append("✅ Gemini AI: Connection stable")
            else:
                results.append(f"❌ Gemini AI: {gemini_msg}")
        else:
            results.append("⚠️ Gemini AI: No API key provided")
        
        # Display results
        for result in results:
            if "✅" in result:
                st.success(result)
            elif "❌" in result:
                st.error(result)
            else:
                st.warning(result)
        
        # Overall status
        if all("✅" in result for result in results):
            st.success("🎉 All connections are stable!")
        else:
            st.warning("⚠️ Some connections need attention.")

def main():
    st.set_page_config(
        page_title="GitHub Trending Scout",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🔍 GitHub Trending Scout")
    st.markdown("*Discover trending repositories for your YouTube content pipeline*")
    
    # Initialize session state for persistent results
    if 'search_results' not in st.session_state:
        st.session_state.search_results = {}
    if 'trending_results' not in st.session_state:
        st.session_state.trending_results = {}
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")
    
    # API Keys
    github_token = st.sidebar.text_input(
        "GitHub Personal Access Token",
        type="password",
        help="Increases rate limit from 60 to 5000 requests/hour"
    )
    
    gemini_api_key = st.sidebar.text_input(
        "Gemini API Key",
        type="password",
        help="Required for AI-powered repository analysis"
    )
    
    # Connection status
    if github_token:
        st.sidebar.success("✅ GitHub token configured")
    else:
        st.sidebar.warning("⚠️ GitHub: Limited to 60 requests/hour")
    
    if gemini_api_key:
        st.sidebar.success("✅ Gemini AI configured")
    else:
        st.sidebar.warning("⚠️ Gemini AI: Basic analysis only")
    
    # Initialize APIs
    scanner = GitHubTrendingScanner(github_token)
    gemini_analyzer = GeminiAnalyzer(gemini_api_key)
    
    st.sidebar.markdown("---")
    
    # Test connections
    test_api_connections(scanner, gemini_analyzer)
    
    st.sidebar.markdown("---")
    
    # Clear results button
    if st.sidebar.button("🗑️ Clear All Results", type="secondary"):
        st.session_state.search_results = {}
        st.session_state.trending_results = {}
        # Clear modal states
        for key in list(st.session_state.keys()):
            if key.startswith('show_modal_') or key.startswith('ai_analysis_'):
                del st.session_state[key]
        st.success("✅ All results cleared!")
        st.rerun()
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["🔥 Trending Scout", "🎯 Custom Search", "💡 Content Ideas"])
    
    with tab1:
        st.header("🔥 Trending Repository Categories")
        
        col1, col2 = st.columns(2)
        
        with col1:
            category = st.selectbox(
                "Choose Content Category",
                [
                    'newly_created',
                    'recently_active', 
                    'breaking_out',
                    'hidden_gems',
                    'ai_ml_trending',
                    'web_dev_trending',
                    'devops_trending',
                    'mobile_trending',
                    'hot_topics'
                ],
                format_func=lambda x: {
                    'newly_created': '🆕 Newly Created (Last 7 days)',
                    'recently_active': '⚡ Recently Active',
                    'breaking_out': '🚀 Breaking Out (100-1000 stars)',
                    'hidden_gems': '💎 Hidden Gems (10-100 stars)',
                    'ai_ml_trending': '🤖 AI/ML Trending',
                    'web_dev_trending': '🌐 Web Dev Trending',
                    'devops_trending': '⚙️ DevOps Trending',
                    'mobile_trending': '📱 Mobile Trending',
                    'hot_topics': '🔥 Hot Topics'
                }[x]
            )
        
        with col2:
            days_back = st.slider("Days to look back", 1, 30, 7)
        
        if st.button("🔍 Scan Trending Repositories", type="primary"):
            with st.spinner("Scanning GitHub for trending repositories..."):
                trending_repos = scanner.scan_trending_by_category(category, days_back)
                st.session_state.trending_results[category] = trending_repos
        
        # Display persistent results
        if category in st.session_state.trending_results:
            trending_repos = st.session_state.trending_results[category]
            
            if trending_repos:
                st.success(f"Found {len(trending_repos)} trending repositories!")
                
                for i, scored_repo in enumerate(trending_repos[:10]):
                    repo = scored_repo['repo']
                    score = scored_repo['score']
                    reasoning = scored_repo['reasoning']
                    
                    with st.expander(f"#{i+1} {repo['full_name']} ⭐ {repo['stargazers_count']:,} (Score: {score:.1f})"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.write(f"**Description:** {repo.get('description', 'No description')}")
                            st.write(f"**Language:** {repo.get('language', 'Unknown')}")
                            st.write(f"**Topics:** {', '.join(repo.get('topics', []))}")
                            st.write(f"**Created:** {repo['created_at'][:10]}")
                            st.write(f"**Reasoning:** {reasoning}")
                        
                        with col2:
                            st.metric("⭐ Stars", f"{repo['stargazers_count']:,}")
                            st.metric("🍴 Forks", f"{repo['forks_count']:,}")
                            st.metric("👀 Watchers", f"{repo['watchers_count']:,}")
                        
                        with col3:
                            st.metric("🐛 Issues", repo['open_issues_count'])
                            st.metric("📚 Wiki", "Yes" if repo.get('has_wiki') else "No")
                            if st.button(f"🤖 Generate AI Analysis", key=f"ai_trending_{i}"):
                                generate_video_content_with_ai(repo, gemini_analyzer)
    
    with tab2:
        st.header("🎯 Custom Repository Search")
        
        col1, col2 = st.columns(2)
        
        with col1:
            custom_query = st.text_input(
                "Custom Search Query",
                placeholder="e.g., language:python stars:>100 created:>2025-08-01"
            )
        
        with col2:
            sort_option = st.selectbox("Sort by", ["stars", "forks", "updated", "created"])
        
        if st.button("🔍 Custom Search") and custom_query:
            with st.spinner("Searching repositories..."):
                repos = scanner.search_repositories(custom_query, sort=sort_option)
                st.session_state.search_results[custom_query] = repos
        
        # Display persistent results
        if custom_query in st.session_state.search_results:
            repos = st.session_state.search_results[custom_query]
            
            if repos:
                st.success(f"Found {len(repos)} repositories!")
                
                for i, repo in enumerate(repos):
                    container = st.container()
                    with container:
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                        
                        with col1:
                            # OPEN IN NEW TAB - Using markdown link
                            st.markdown(f"### 📂 [{repo['full_name']}]({repo['html_url']})")
                            st.caption(repo.get('description', 'No description')[:100] + '...' if repo.get('description') else 'No description')
                            
                            # Details button
                            if st.button(f"🔍 View Details", key=f"details_btn_{i}"):
                                st.session_state[f'show_modal_{i}'] = True
                        
                        with col2:
                            st.metric("⭐", f"{repo['stargazers_count']:,}")
                        with col3:
                            st.metric("🍴", f"{repo['forks_count']:,}")
                        with col4:
                            st.write(f"**{repo.get('language', 'Unknown')}**")
                        with col5:
                            st.write(f"{repo['created_at'][:10]}")
                    
                    # Modal functionality
                    if st.session_state.get(f'show_modal_{i}', False):
                        show_repo_details_modal(repo, f"custom_{i}", gemini_analyzer)
                        if st.button("❌ Close Details", key=f"close_modal_{i}"):
                            st.session_state[f'show_modal_{i}'] = False
                            st.rerun()
                        st.markdown("---")
    
    with tab3:
        st.header("💡 Content Ideas Generator")
        
        if st.button("🎬 Generate Content Ideas"):
            content_ideas = [
                "🔥 'This Repository is Breaking GitHub!' - Focus on rapid growth stories",
                "💎 'Hidden Gem Alert' - Showcase undervalued high-quality repos",
                "⚔️ 'Repo Battle' - Compare similar libraries/frameworks",
                "🚀 'From Zero to Hero' - Track a repository's growth journey",
                "🤖 'AI Tool of the Week' - Spotlight trending AI repositories",
                "🌟 'Developer Spotlight' - Interview major contributors",
                "🔍 'Why is Everyone Talking About...' - Analyze viral repos",
                "📚 'Learning Path' - Curate repositories for skill development"
            ]
            
            for idea in content_ideas:
                st.write(f"• {idea}")
        
        st.subheader("📝 AI-Powered Video Production Workflow")
        workflow_steps = [
            "1. 🔍 **Discover** - Use Trending Scout to find interesting repositories",
            "2. 🤖 **AI Analysis** - Click 'Generate AI Analysis' for comprehensive research",
            "3. 📚 **NotebookLM** - Download analysis and upload to NotebookLM for podcast generation",
            "4. 🎤 **Audio** - Use NotebookLM's generated podcast as your voiceover base",
            "5. 🎨 **Visuals** - Add code examples, repository screenshots, and animations",
            "6. ✂️ **Edit** - Combine audio, visuals, and add captions",
            "7. 📤 **Publish** - Upload to YouTube with AI-generated titles and tags"
        ]
        
        for step in workflow_steps:
            st.markdown(step)
        
        st.info("💡 **Pro Tip**: The AI analysis is specifically formatted for NotebookLM - just download the markdown file and upload it to create professional podcast content!")

if __name__ == "__main__":
    main()
