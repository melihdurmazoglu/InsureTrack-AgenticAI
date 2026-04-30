
# InsureTrack-AgenticAI
An autonomous Agentic AI system for insurance and technology news curation.



# 1. Team Members
Melih Durmazoğlu

---

# 2. Project Motivation
The insurance industry is undergoing a rapid digital transformation driven by artificial intelligence. Staying updated with the latest trends, sector-specific news, and competitor moves is crucial for maintaining a competitive edge. As an intern in this field, I realized that manually tracking these updates is time-consuming and prone to human error. This project aims to automate this knowledge-gathering process using an intelligent agent that acts like a specialized digital journalist.

---

### 3. The Problem
 **Field**: _Data Science / Agentic AI applied to Insurance and Corporate Intelligence._
 
**The Problem**

-**Information Overload:** Thousands of news articles are published daily, making it hard to filter what is relevant to the insurance sector and AI.  
-**Manual Effort**: Compiling monthly technology bulletins requires significant manual research. 
-**Lack of Structure:** Information is scattered across various sources without a unified categorical view.

### The Solution: 
An autonomous agent that can search, filter, and categorize news into four specific pillars: About insurance company, Insurance Sector, Insurance & Tech, and Artificial Intelligence.

---

## 4. Project Plan & Methodology
Throughout this semester, the following steps will be executed:

**Agentic Architecture:** Developing a system with an **autonomous decision loop** where the agent decides which search queries to execute based on the monthly context.

**Categorization & Summarization:** Using LLMs to categorize news and generate concise summaries for professional use.

**Evaluation Framework:** Implementing an **LLM-in-the-loop** system to verify if the gathered news matches the specified categories and quality standards.

**Deployment:** The project will be deployed on **Hugging Face** with a **Streamlit** interface.


---
---


## Technical Part

### Architecture

Single-agent, tool-augmented ReAct loop

The agent autonomously decides which search queries to execute, evaluates the results, and iterates until sufficient information is gathered.

**Pipeline:**

```
User / Timer → LangGraph ReAct Agent → Tavily Search Tool → Internet (live news)
                                                          ↓
                                         Claude Haiku (LLM)
                                                          ↓
                                    Markdown Parser + ReportLab
                                                          ↓
                                                    PDF Output
```

---

### Frameworks

**Agentics:** LangGraph and LangChain are used as the agent framework. The agent doesn't just follow a prompt; it makes decisions and searches within a loop, making it a ReAct Agent.

**LLM:** Claude Haiku 4.5 was selected as the primary model due to its speed and cost efficiency, which are important for a monthly automated pipeline. Gemini 1.5 Flash was also tested during early development but was set aside due to inconsistent output formatting.

**Search Tool:** Tavily Search API was used as the search tool, as it is optimized for AI agents.

**PDF Engine:** ReportLab was chosen for its full integration with Python and dynamic content management. Since news articles vary in length, this flexibility was considered an advantage.

---

### Data Sources

This project does not rely on a static dataset. Instead, the agent dynamically retrieves real-time news through the Tavily Search API, which aggregates results from across the web. To ensure relevance, eight predefined query templates were crafted across two categories: Insurance & Technology, and General Technology. These queries were designed based on domain knowledge of the insurance sector, targeting specific topics such as insurtech investments, AI-driven claims processing, and regulatory developments.

---

### Evaluation Plan

At this stage, bulletin quality is checked manually by reviewing whether the news items are relevant and correctly categorized. In the next phase, a second Claude Haiku call will be added to automatically verify each news item checking if it actually fits its assigned category. This removes the need for manual review and makes the evaluation process scalable.

---

### User Interface

A web-based interface is planned using Streamlit. Users will be able to trigger bulletin generation manually, track its progress in real time, and download previously generated PDF bulletins.

---

### Team Responsibilities

| Role | Responsibility | Member |
|---|---|---|
| Agent Architecture | Designing the ReAct loop, query templates | Melih Durmazoğlu |
| Prompt Engineering | LLM prompt | Melih Durmazoğlu |
| Output & Formatting | PDF creation, layout design, Turkish character handling | Melih Durmazoğlu |
| Scheduler & Deployment | Windows Task Scheduler integration, automation setup | Melih Durmazoğlu |
| UI Development *(planned)* | Streamlit interface design and integration | Melih Durmazoğlu |
