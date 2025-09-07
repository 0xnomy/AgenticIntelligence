# Agentic Intelligence

A SaaS platform for automated market intelligence using AI agents.

## What it does

Agentic Intelligence collects product data from e-commerce websites, performs deep market analysis using AI, provides a Q&A chatbot for insights, and generates business reports.

## How it works

1. **Data Scraping**: Uses Playwright to scrape product information from multiple e-commerce sources.
2. **Market Analysis**: Leverages Groq LLM to analyze trends, compare products, and identify opportunities.
3. **Q&A Chatbot**: Answers questions about market data using AI-generated insights.
4. **Report Generation**: Creates comprehensive business reports for decision-making.

## APIs Used

- Groq API (for AI analysis and chatbot)
- Playwright (for web scraping)

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables: `GROQ_API_KEY`, `SECRET_KEY`
4. Run: `uvicorn main:app --reload`

## License

This project is licensed under the MIT License.
