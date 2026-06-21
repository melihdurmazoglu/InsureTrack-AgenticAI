---
title: InsureTrack AgenticAI
emoji: 📰
colorFrom: blue
colorTo: green
sdk: docker
app_file: app.py
pinned: false
---

# InsureTrack — Autonomous AI News Curator

An autonomous Agentic AI system that searches, evaluates, and compiles monthly insurance & technology bulletins into professional PDF reports.

🔗 **[Live Demo on Hugging Face Spaces](https://huggingface.co/spaces/melihdurmazoglu/InsureTrack-AgenticAI)**  
📝 **[Project Blog Post on Medium](https://medium.com/@melihdurmazoglu35/insuretrack-autonomous-ai-news-curator-25aeb730a426)**  
💻 **[GitHub Repository](https://github.com/melihdurmazoglu/InsureTrack-AgenticAI)**

---

## Team Members

| Name | Role |
|---|---|
| Melih Durmazoğlu | Full-stack development, agent architecture, deployment |

---

## Project Motivation

The insurance industry is undergoing rapid digital transformation driven by artificial intelligence. Staying updated with the latest trends and sector-specific news is crucial for professionals in the field. As an intern in this sector, I realized that manually tracking these updates is time-consuming and error-prone.

This project automates the knowledge-gathering process using an intelligent agent that acts like a specialized digital journalist — autonomously searching, filtering, evaluating, and packaging news into a structured monthly report.

---

## The Problem

**Field:** Data Science / Agentic AI applied to Insurance and Corporate Intelligence.

- **Information Overload:** Thousands of news articles are published daily; filtering what is relevant to the insurance sector requires significant effort.
- **Manual Effort:** Compiling monthly technology bulletins requires substantial research time.
- **Lack of Structure:** Information is scattered across sources without a unified categorical view.

**The Solution:** An autonomous agent that searches, filters, evaluates, and categorizes news into two pillars: **Insurance & Technology** and **General Technology**, then exports a professional PDF bulletin.

---

## Architecture

Single-agent, tool-augmented ReAct loop with an LLM-in-the-loop evaluation layer.

```
User (Streamlit UI)
        │
        ▼
LangGraph ReAct Agent  ──────►  Tavily Search API  ──►  Live Web
        │
        ▼
 Claude Haiku 4.5 (LLM)
        │
        ▼
 Evaluation Agent (Claude Haiku 4.5)
        │
        ├── GECTI (score ≥ 7/10) ──► PDF Generation (ReportLab)
        │
        └── KALDI (score < 7/10) ──► Re-search → Re-evaluate → PDF
                                            ▲
                                  (autonomous retry loop)
        │
        ▼
  Streamlit Interface
  (progress tracking + PDF download)
```

**Key agentic properties:**
- The agent autonomously decides which search queries to execute and iterates until sufficient quality is reached
- A second LLM call (evaluation agent) verifies each news item — this is the "LLM-in-the-loop" component required for agentic systems
- If items fail evaluation, the agent autonomously re-searches and replaces them (autonomous decision loop)

---

## Frameworks & Tools

| Component | Technology | Reason |
|---|---|---|
| Agent Framework | LangGraph + LangChain | ReAct loop, tool use, autonomous iteration |
| LLM | Claude Haiku 4.5 | Speed and cost efficiency for monthly automation |
| Search Tool | Tavily Search API | Optimized for AI agents, real-time web results |
| PDF Engine | ReportLab | Full Python integration, dynamic content, Turkish character support |
| Web Interface | Streamlit | Rapid deployment, real-time progress tracking |
| Deployment | Hugging Face Spaces (Docker) | Public accessibility, persistent storage |
| CI/CD | GitHub Actions | Automatic sync from GitHub → Hugging Face on every push |

---

## Data Sources

This project does not rely on a static dataset. The agent dynamically retrieves real-time news through the Tavily Search API across two categories:

**Category 1 — Insurance & Technology (10 news items)**
Targets insurtech investments, AI-driven claims processing, regulatory developments, and digital transformation in insurance.

**Category 2 — General Technology (10 news items)**
Targets new AI model releases, semiconductor developments, and major tech company announcements.

Query templates are crafted based on domain knowledge of the insurance sector and updated monthly with the current date context.

---

## Evaluation Framework

The system implements a two-stage LLM-in-the-loop evaluation:

**Stage 1 — Initial Evaluation**
After the agent collects 20 news items, a second Claude Haiku call evaluates each item on four criteria (each 0–10):

| Criterion | Description |
|---|---|
| URL Score | Is a valid, complete URL present? |
| Date Score | Is the article from the last 30 days? |
| Category Score | Does the article fit its assigned category? |
| Content Score | Is the title meaningful and relevant? |

**Decision rule:** Average ≥ 7 → **GEÇTİ (PASS)**, Average < 7 → **KALDI (FAIL)**

**Stage 2 — Autonomous Retry**
Items that fail evaluation trigger an autonomous re-search loop: the agent searches for a replacement article in the same category and re-evaluates. This loop continues until all items pass or no better alternatives are found.

**Sample evaluation result from a real run:**

```
──────────────────────────────────────────────
  📋 EVALUATİON SONUCU
──────────────────────────────────────────────
  ✅ [9.0/10] Insurtech Insights USA 2026 - AI Takes Center Stage...
  ✅ [8.8/10] Allstate AI Agent Handles 250K Conversations Monthly...
  ✅ [9.2/10] Microsoft Build 2026 - MAI Models Announced...
  ...
──────────────────────────────────────────────
  Genel Ortalama : 8.8/10
  Geçen Haberler : 20
  Kalan Haberler : 0
  Genel Karar    : GEÇTİ
──────────────────────────────────────────────
```

The evaluation report is embedded directly into the generated PDF as a "Quality Report" section.

---

## User Interface

The Streamlit web interface allows users to:

- **Trigger bulletin generation manually** with a single button click
- **Track progress in real time** via an expandable status panel showing each pipeline step
- **Download the generated PDF** immediately after completion
- **Browse past bulletins** with one-click download for each previous report

The interface is deployed on Hugging Face Spaces via Docker and is publicly accessible.

---

## Deployment & CI/CD

The project is deployed on **Hugging Face Spaces** using a Docker container.

**Automatic sync pipeline:**
1. Code is pushed to the GitHub repository
2. A GitHub Actions workflow triggers automatically
3. The workflow pushes the updated code to the Hugging Face Space
4. The Space rebuilds and redeploys — zero manual steps required

API keys (Anthropic + Tavily) are stored as **Hugging Face Secrets** and injected at runtime — never hardcoded in the repository.

---

## Team Responsibilities

| Role | Responsibility | Member | Status |
|---|---|---|---|
| Agent Architecture | ReAct loop design, query templates | Melih Durmazoğlu | ✅ Complete |
| Prompt Engineering | LLM prompts for agent + evaluator | Melih Durmazoğlu | ✅ Complete |
| Evaluation Framework | LLM-in-the-loop quality scoring + retry loop | Melih Durmazoğlu | ✅ Complete |
| Output & Formatting | PDF creation, layout, Turkish character handling | Melih Durmazoğlu | ✅ Complete |
| UI Development | Streamlit interface, progress tracking, download | Melih Durmazoğlu | ✅ Complete |
| Deployment | Docker, Hugging Face Spaces, GitHub Actions CI/CD | Melih Durmazoğlu | ✅ Complete |
