# 🔍 GitHub Trending Scout

> **AI-Powered Repository Discovery for YouTube Content Creation**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![GitHub API](https://img.shields.io/badge/GitHub-API-black.svg)](https://docs.github.com/en/rest)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-orange.svg)](https://makersuite.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**GitHub Trending Scout** is an AI-powered tool that helps content creators discover trending repositories and generate comprehensive video content automatically. Perfect for YouTubers, developers, and tech content creators who want to stay on top of the latest GitHub trends.

## ✨ Features

### 🔥 **Trending Repository Discovery**
- **9 Content Categories**: AI/ML, Web Dev, DevOps, Mobile, Hidden Gems, and more
- **Smart Scoring Algorithm**: Multi-factor scoring based on stars, forks, activity, and recency
- **Customizable Time Ranges**: Search repositories from last 1-30 days
- **Persistent Results**: Search results stay until manually cleared

### 🤖 **AI-Powered Analysis**
- **Comprehensive Repository Analysis**: Technical details, community insights, content opportunities
- **NotebookLM Ready Output**: Structured content perfect for AI podcast generation
- **Video Content Strategy**: Auto-generated titles, tags, and target audience analysis
- **Natural Language Search**: Convert plain English to GitHub API syntax

### 🎯 **Advanced Search Capabilities**
- **Natural Language Queries**: "Python machine learning repos with 100+ stars"
- **GitHub API Integration**: Full access to GitHub's search capabilities
- **Smart Query Conversion**: AI converts natural language to proper GitHub syntax
- **Multiple Sort Options**: Sort by stars, forks, recent updates, or creation date

### 📊 **Content Creation Pipeline**
- **Video Title Generation**: 5 optimized titles per repository
- **SEO Tag Suggestions**: Relevant tags for YouTube optimization
- **Target Audience Analysis**: Identify your ideal viewer demographic
- **Upload Time Recommendations**: Best posting schedules by content type

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- GitHub account (for API access)
- Google AI Studio account (for Gemini API)

### Installation

1. **Clone the repository**
git clone https://github.com/yourusername/github-trending-scout.git
cd github-trending-scout


2. **Install dependencies**
pip install streamlit requests pandas plotly python-dateutil google-generativeai


3. **Run the application**
streamlit run app.py


4. **Open in browser**
- Application will open at `http://localhost:8501`

### API Setup

#### GitHub Personal Access Token (Recommended)
1. Go to [GitHub Settings](https://github.com/settings/tokens)
2. Click "Developer settings" → "Personal access tokens"
3. Generate new token (classic) with `public_repo` scope
4. Copy the token and paste in the sidebar

**Benefits**: Increases rate limit from 60 to 5,000 requests/hour

#### Gemini AI API Key (Required for AI features)
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and paste in the sidebar

**Benefits**: Enables natural language search and AI-powered repository analysis

## 📖 Usage Guide

### 🔥 Trending Scout

**Discover trending repositories by category:**

1. **Select Category**:
- 🆕 Newly Created - Fresh repositories (last 7 days)
- 🚀 Breaking Out - Mid-tier repos (100-1000 stars) with potential
- 💎 Hidden Gems - Quality projects under 100 stars
- 🤖 AI/ML Trending - Machine learning repositories
- 🌐 Web Dev Trending - Frontend and web development
- ⚙️ DevOps Trending - Infrastructure and deployment tools

2. **Adjust Parameters**: Set days to look back (1-30 days)

3. **Generate Analysis**: Click "🤖 Generate AI Analysis" for any repository

### 🎯 Custom Search

**Use natural language to find specific repositories:**

Examples:

"Python machine learning repositories with more than 100 stars"

"Recent JavaScript projects created this year"

"Beginner friendly Python projects with good documentation"

"Rust web frameworks updated in the last 6 months"

"Docker containers for data science applications"



### 🤖 AI Analysis Output

Each analysis includes:
- **Repository Overview**: Problem solved, target audience, unique features
- **Technical Analysis**: Technologies, architecture, code quality
- **Community & Adoption**: Engagement metrics, real-world usage
- **Content Opportunities**: Video angles, talking points, trends
- **Practical Insights**: Getting started, use cases, learning curve

### 📥 Export Options
- **📋 Copy to Clipboard**: Display content for manual copying
- **📥 Download as Markdown**: Perfect for NotebookLM upload
- **👁️ Preview Analysis**: Read-only preview of full content

## 🎬 Content Creation Workflow

### Complete YouTube Automation Pipeline:

1. **🔍 Discover** - Use Trending Scout or natural search
2. **🤖 Analyze** - Generate AI-powered repository research  
3. **📚 NotebookLM** - Upload analysis for AI podcast generation
4. **🎤 Audio** - Use NotebookLM's podcast as voiceover base
5. **🎨 Visuals** - Add code examples, screenshots, animations
6. **✂️ Edit** - Combine audio + visuals + captions
7. **📤 Publish** - Upload with AI-generated titles and tags

## 🛠️ Technical Details

### Architecture
- **Frontend**: Streamlit web interface
- **Backend**: Python with GitHub REST API integration
- **AI Engine**: Google Gemini for natural language processing
- **Data Processing**: Pandas for repository analytics
- **Visualization**: Plotly for metrics and charts

### Scoring Algorithm
final_score = (base_popularity + activity_score) * recency_multiplier * language_boost

Where:

base_popularity = stars * 1.0 + forks * 2.0 + watchers * 1.5

activity_score = issues * 0.1 + wiki_bonus + topics_bonus

recency_multiplier = based on repository age

language_boost = popularity multiplier per programming language


### Rate Limits
- **GitHub API (no token)**: 60 requests/hour
- **GitHub API (with token)**: 5,000 requests/hour
- **Gemini API**: Based on your Google AI Studio quota

## 📊 Example Outputs

### Video Title Examples:
- "This Python Repository Has 15,000 Stars - Here's Why"
- "FastAPI: The Tool Every Developer Needs to Know About"
- "Why Everyone's Talking About This Rust Web Framework"

### Generated Tags:
`github, python, fastapi, webdev, api, backend, programming, coding, opensource, developer`

### Target Audiences:
- **AI/ML Projects**: "AI/ML Engineers, Data Scientists"
- **Web Development**: "Frontend Developers, Full-stack Engineers"
- **DevOps Tools**: "DevOps Engineers, System Administrators"

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Setup
Clone your fork
git clone https://github.com/yourusername/github-trending-scout.git

Install development dependencies
pip install -r requirements-dev.txt

Run with debug mode
streamlit run app.py --server.runOnSave true


## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **GitHub API** - For providing comprehensive repository data
- **Google Gemini** - For powering natural language processing
- **Streamlit** - For the amazing web framework
- **NotebookLM** - For AI-powered podcast generation
- **Open Source Community** - For inspiration and feedback

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/github-trending-scout/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/github-trending-scout/discussions)
- **Email**: your.email@example.com

## 🗺️ Roadmap

- [ ] **YouTube API Integration** - Direct video upload
- [ ] **Trending Predictions** - ML models for trend forecasting
- [ ] **Multi-language Support** - Interface localization
- [ ] **Repository Comparison** - Side-by-side analysis
- [ ] **Historical Tracking** - Repository growth over time
- [ ] **Chrome Extension** - Browser integration
- [ ] **Mobile App** - iOS/Android versions

---

<div align="center">

**⭐ Star this repository if it helped you create amazing content!**

[**🚀 Try GitHub Trending Scout**](https://github.com/yourusername/github-trending-scout) 
• [**📚 Documentation**](https://github.com/yourusername/github-trending-scout/wiki) 
• [**🐛 Report Bug**](https://github.com/yourusername/github-trending-scout/issues)

</div>
