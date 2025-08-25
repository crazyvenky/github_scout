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
import base64

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
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                st.error(f"Failed to initialize Gemini: {e}")
                self.model = None
    
    def test_connection(self):
        """Test Gemini API connection"""
        if not self.api_key or not self.model:
            return False, "No API key provided"
        
        try:
            response = self.model.generate_content("Hello, this is a connection test.")
            if response.text:
                return True, "Connected successfully"
            else:
                return False, "No response received"
        except Exception as e:
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
    
    def convert_natural_to_github_query(self, natural_query: str) -> str:
        """Convert natural language to GitHub API search syntax"""
        if not self.model:
            return natural_query  # Return as-is if no Gemini API
        
        prompt = f"""
Convert this natural language search query into proper GitHub API search syntax:

Natural Query: "{natural_query}"

GitHub API supports these search qualifiers:
- language:python (for programming language)
- stars:>100 or stars:10..50 (for star count ranges)
- forks:>10 (for fork count)
- created:>2023-01-01 or created:2023-01-01..2024-01-01 (for date ranges)
- pushed:>2024-01-01 (for recent activity)
- topic:machine-learning (for repository topics)
- user:microsoft (for specific users/organizations)
- in:name (search in repository name)
- in:description (search in repository description)
- in:readme (search in README)
- good-first-issues:>1 (repositories with good first issues)
- help-wanted-issues:>1 (repositories seeking help)
- license:mit (for specific licenses)
- archived:false (exclude archived repositories)

Examples:
- "Python machine learning repositories with more than 100 stars" → "language:python topic:machine-learning stars:>100"
- "Recent JavaScript projects created this year" → "language:javascript created:>2024-01-01"
- "Popular React libraries with good documentation" → "language:javascript topic:react stars:>500 in:readme"
- "Beginner friendly Python projects" → "language:python good-first-issues:>1 stars:>10"

Convert the natural query to proper GitHub search syntax. Return ONLY the search query, no explanations:
"""

        try:
            response = self.model.generate_content(prompt)
            converted_query = response.text.strip()
            # Clean up any extra quotes or formatting
            converted_query = converted_query.replace('"', '').replace("'", '').strip()
            return converted_query
        except Exception as e:
            st.warning(f"Could not convert query using AI: {e}")
            return natural_query
    
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
            response = self.model.generate_content(prompt)
            return response.text if response.text else "❌ No response generated"
        except Exception as e:
            return f"❌ Error analyzing repository: {str(e)}"

def create_download_link(content, filename):
    """Create a download link for content"""
    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:text/markdown;base64,{b64}" download="{filename}">Download {filename}</a>'

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
        if st.button(f"🤖 Generate AI Analysis", key=f"video_{key_suffix}"):
            generate_video_content_with_ai(repo, gemini_analyzer)

def generate_video_content_with_ai(repo, gemini_analyzer):
    """Generate video content with AI analysis from Gemini"""
    
    # Get AI analysis
    if gemini_analyzer and gemini_analyzer.model:
        with st.spinner("🤖 Generating AI analysis..."):
            ai_analysis = gemini_analyzer.analyze_repository(repo['html_url'], repo)
    else:
        ai_analysis = "⚠️ Gemini API not configured. Using basic template."
    
    # Content analysis
    content_type = determine_content_type(repo)
    titles = generate_video_titles(repo)
    tags = generate_video_tags(repo)
    
    # Create comprehensive notebook content
    notebook_content = f"""# Repository Analysis: {repo['full_name']}

## Repository Information
- **Name:** {repo['full_name']}
- **URL:** {repo['html_url']}
- **Description:** {repo.get('description', 'No description available')}
- **Language:** {repo.get('language', 'Unknown')}
- **Stars:** {repo['stargazers_count']:,}
- **Forks:** {repo['forks_count']:,}
- **Created:** {repo['created_at'][:10]}
- **Topics:** {', '.join(repo.get('topics', []))}

## AI-Generated Analysis

{ai_analysis}

## Video Production Notes
- **Content Type:** {content_type}
- **Target Audience:** {get_target_audience(repo)}
- **Estimated Length:** 8-12 minutes
- **Best Upload Time:** {get_optimal_upload_time(repo)}

## Suggested Video Titles
{chr(10).join([f"- {title}" for title in titles])}

## Video Tags
{', '.join(tags)}

## Key Talking Points
- Repository has {repo['stargazers_count']:,} stars and {repo['forks_count']:,} forks
- Created on {repo['created_at'][:10]}
- Main programming language: {repo.get('language', 'Unknown')}
- {"Has wiki documentation" if repo.get('has_wiki') else "No wiki documentation"}
- {repo['open_issues_count']} open issues

---
*Generated by GitHub Trending Scout with Gemini AI Analysis*
"""
    
    st.success(f"✅ AI analysis completed for {repo['full_name']}!")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Copy to clipboard button
        if st.button("📋 Copy Analysis", key=f"copy_{repo['id']}"):
            st.code(notebook_content)
            st.success("✅ Analysis displayed above - you can select and copy it!")
    
    with col2:
        # Download button
        st.download_button(
            label="📥 Download Analysis",
            data=notebook_content,
            file_name=f"{repo['name']}_analysis.md",
            mime="text/markdown",
            key=f"download_{repo['id']}"
        )
    
    with col3:
        # Open in new tab (using JavaScript)
        if st.button("🔗 Open in New Tab", key=f"newtab_{repo['id']}"):
            # Store content in session state and provide instructions
            st.session_state[f'analysis_content_{repo["id"]}'] = notebook_content
            st.info("💡 **To open in new tab:** Use the download button and then open the file in your preferred text editor or browser.")
    
    # Show preview (do NOT use expander here to avoid nesting error)
    st.markdown("### 👁️ Preview Analysis")
    st.text_area(
        "Analysis Content (Read-only preview)",
        notebook_content,
        height=300,
        disabled=True,
        key=f"preview_{repo['id']}"
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

def show_help_readme():
    """Display help and usage instructions"""
    st.markdown("""
# 📖 GitHub Trending Scout - User Guide

## 🚀 Quick Start

### 1. Setup API Keys
- **GitHub Token** (Optional but recommended): Increases API limit from 60 to 5000 requests/hour
  - Go to GitHub Settings → Developer settings → Personal access tokens
  - Generate new token with `public_repo` scope
- **Gemini API Key** (Required for AI features): Enables natural language search and AI analysis
  - Get your key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### 2. Test Connections
- Click "🔍 Test All Connections" in the sidebar to verify your setup
- Green checkmarks = everything is working!

## 🔥 Trending Scout Tab

### Categories Available:
- **🆕 Newly Created**: Repositories created in the last X days
- **⚡ Recently Active**: Repos with recent commits and decent star count
- **🚀 Breaking Out**: Mid-tier repositories (100-1000 stars) with potential
- **💎 Hidden Gems**: Quality projects with low star count (10-100 stars)
- **🤖 AI/ML Trending**: Machine learning and AI repositories
- **🌐 Web Dev Trending**: React, frontend, and web development tools
- **⚙️ DevOps Trending**: Docker, Kubernetes, and infrastructure tools
- **📱 Mobile Trending**: Android, iOS, and mobile development
- **🔥 Hot Topics**: Repositories with good first issues

### How to Use:
1. Select a category from the dropdown
2. Adjust "days to look back" slider (1-30 days)
3. Click "🔍 Scan Trending Repositories"
4. Results persist until you clear them or run a new search
5. Click "🤖 Generate AI Analysis" on any repository for detailed content

## 🎯 Custom Search Tab

### Natural Language Search (AI-Powered)
Instead of learning complex GitHub search syntax, just type what you want in plain English!

#### Examples of Natural Language Queries:
- "Python machine learning repositories with more than 100 stars"
- "Recent JavaScript projects created this year"
- "Beginner friendly Python projects"
- "Popular React libraries with good documentation"
- "Rust web frameworks created in the last 6 months"
- "Go microservices tools with more than 50 forks"
- "TypeScript testing libraries updated recently"
- "Docker containers for data science"
- "Mobile app development frameworks"
- "Blockchain projects in Solidity"

#### The AI Will Convert These To:
- `language:python topic:machine-learning stars:>100`
- `language:javascript created:>2024-01-01`
- `language:python good-first-issues:>1 stars:>10`
- `language:javascript topic:react stars:>500 in:readme`
- `language:rust topic:web created:>2024-02-01`
- `language:go topic:microservices forks:>50`
- `language:typescript topic:testing pushed:>2024-08-01`
- `language:dockerfile topic:data-science`
- `topic:mobile language:swift OR language:kotlin`
- `language:solidity topic:blockchain`

### Advanced GitHub Search Syntax (Manual)
If you prefer direct control, you can use GitHub's search syntax:

#### Language Filters:
- `language:python` - Python repositories
- `language:javascript` - JavaScript repositories  
- `language:typescript` - TypeScript repositories
- `language:rust` - Rust repositories
- `language:go` - Go repositories

#### Star/Fork Filters:
- `stars:>100` - More than 100 stars
- `stars:10..50` - Between 10 and 50 stars
- `forks:>10` - More than 10 forks
- `watchers:>5` - More than 5 watchers

#### Date Filters:
- `created:>2024-01-01` - Created after January 1, 2024
- `pushed:>2024-08-01` - Active since August 1, 2024
- `created:2023-01-01..2024-01-01` - Created in 2023

#### Topic Filters:
- `topic:machine-learning` - AI/ML repositories
- `topic:react` - React projects
- `topic:docker` - Docker-related projects
- `topic:api` - API projects

#### Quality Indicators:
- `good-first-issues:>1` - Beginner-friendly projects
- `help-wanted-issues:>1` - Projects seeking contributors  
- `has:wiki` - Projects with documentation wikis
- `archived:false` - Exclude archived projects

#### Search Location:
- `in:name` - Search in repository name
- `in:description` - Search in repository description
- `in:readme` - Search in README file

## 🤖 AI Analysis Features

### What You Get:
1. **Repository Overview**: Problem it solves, target audience, unique features
2. **Technical Analysis**: Technologies used, architecture, code quality
3. **Community & Adoption**: Engagement metrics, real-world usage, contributors
4. **Content Opportunities**: Why it's trending, video angles, talking points
5. **Comparison & Context**: How it compares to alternatives, ecosystem fit
6. **Practical Insights**: Getting started, use cases, learning curve

### Output Options:
- **📋 Copy Analysis**: Display content for manual copying
- **📥 Download Analysis**: Download as `.md` file for NotebookLM
- **🔗 Open in New Tab**: Instructions for viewing in external editor
- **👁️ Preview**: Read-only preview of the full analysis

## 💡 Content Ideas Tab

### Video Series Suggestions:
- **Repository Spotlights**: Deep dives into interesting projects
- **Hidden Gems**: Showcase undervalued repositories
- **Repo Battles**: Compare similar tools/frameworks
- **Growth Stories**: Track how repositories gain popularity
- **Developer Tools**: Review practical development utilities

### Production Workflow:
1. **Discover**: Find repositories using Trending Scout
2. **Analyze**: Generate AI-powered research with one click
3. **Script**: Use the analysis as your video script foundation
4. **Record**: Upload to NotebookLM for AI-generated podcasts
5. **Visualize**: Add code examples, screenshots, animations
6. **Publish**: Use generated titles and tags for optimization

## ⚠️ Important Notes

### Rate Limits:
- **Without GitHub token**: 60 requests/hour
- **With GitHub token**: 5000 requests/hour
- **Gemini API**: Check your quota in Google AI Studio

### Best Practices:
- Test your API connections before starting
- Use natural language for custom search - it's much easier!
- Download AI analyses for offline use and NotebookLM upload
- Clear results periodically to free up memory
- Repository links open in new tabs for easy exploration

### Troubleshooting:
- **No results found**: Try broader search terms or adjust date ranges
- **API errors**: Check your tokens and rate limits
- **Gemini not working**: Verify your API key in Google AI Studio
- **Search syntax errors**: Use natural language instead of manual syntax

## 🎬 NotebookLM Integration

The AI analysis is specifically formatted for NotebookLM:
1. Download the analysis as a `.md` file
2. Upload to [NotebookLM](https://notebooklm.google.com)
3. Generate an AI podcast discussion
4. Use as your video voiceover or inspiration
5. Add visuals, code examples, and your own commentary

---

*Happy repository hunting! 🚀*
    """)

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
        help="Required for AI-powered repository analysis and natural language search"
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
    tab1, tab2, tab3, tab4 = st.tabs(["🔥 Trending Scout", "🎯 Custom Search", "💡 Content Ideas", "📖 Help & Guide"])
    
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
        
        # Help section for natural language search
        with st.expander("💡 How to Search (Click to expand)", expanded=False):
            st.markdown("""
            ### 🗣️ Natural Language Search (AI-Powered)
            Just type what you want in plain English! The AI will convert it to proper GitHub syntax.
            
            **Examples:**
            - "Python machine learning repositories with more than 100 stars"
            - "Recent JavaScript projects created this year"  
            - "Beginner friendly Python projects"
            - "Popular React libraries with good documentation"
            - "Rust web frameworks created in the last 6 months"
            
            ### ⚙️ Manual GitHub Syntax (Advanced)
            If you prefer direct control:
            - `language:python stars:>100` - Python repos with 100+ stars
            - `created:>2024-01-01` - Created this year
            - `topic:machine-learning` - ML repositories
            - `good-first-issues:>1` - Beginner friendly
            """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            natural_query = st.text_area(
                "🗣️ Natural Language Search (AI-Powered)",
                placeholder="Example: Python machine learning repositories with more than 100 stars created this year",
                height=100,
                help="Describe what you're looking for in plain English. AI will convert it to GitHub search syntax."
            )
        
        with col2:
            sort_option = st.selectbox("Sort by", ["stars", "forks", "updated", "created"])
            
            if gemini_analyzer.api_key:
                st.success("✅ AI-powered natural language search enabled")
            else:
                st.warning("⚠️ Add Gemini API key for natural language search")
        
        if st.button("🔍 Search Repositories", type="primary") and natural_query:
            with st.spinner("Converting query and searching repositories..."):
                # Convert natural language to GitHub syntax if Gemini is available
                if gemini_analyzer.api_key:
                    github_query = gemini_analyzer.convert_natural_to_github_query(natural_query)
                    st.info(f"🤖 AI converted your query to: `{github_query}`")
                else:
                    github_query = natural_query
                    st.info(f"🔍 Searching with: `{github_query}`")
                
                repos = scanner.search_repositories(github_query, sort=sort_option)
                st.session_state.search_results[natural_query] = repos
        
        # Display persistent results
        if natural_query in st.session_state.search_results:
            repos = st.session_state.search_results[natural_query]
            
            if repos:
                st.success(f"Found {len(repos)} repositories!")
                
                for i, repo in enumerate(repos):
                    container = st.container()
                    with container:
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                        
                        with col1:
                            # Repository link opens in new tab
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
            "1. 🔍 **Discover** - Use Trending Scout or natural language search to find repositories",
            "2. 🤖 **AI Analysis** - Click 'Generate AI Analysis' for comprehensive research",
            "3. 📥 **Download** - Download analysis as markdown file for NotebookLM",
            "4. 🎤 **NotebookLM** - Upload to [NotebookLM](https://notebooklm.google.com) for AI podcast generation",
            "5. 🎨 **Visuals** - Add code examples, repository screenshots, and animations",
            "6. ✂️ **Edit** - Combine AI-generated audio with visuals and add captions",
            "7. 📤 **Publish** - Upload to YouTube with AI-generated titles and tags"
        ]
        
        for step in workflow_steps:
            st.markdown(step)
        
        st.info("💡 **Pro Tip**: The AI analysis is specifically formatted for NotebookLM - just download and upload to create professional podcast content!")
    
    with tab4:
        show_help_readme()

if __name__ == "__main__":
    main()
