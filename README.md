# Agentic Intelligence

A multi-agent SaaS platform for automated market intelligence. Scrapes product data from e-commerce sites, performs deep AI-powered analysis, answers user questions, and generates business reports. Built with FastAPI, Playwright, LangGraph, and a modern HTML/JS frontend.

---

## Features

- **User Authentication:** Secure registration and login with JWT tokens.
- **Automated Scraping:** Scrapes product data from multiple e-commerce sources (currently Breakout and Rastah).
- **Data Storage:** All scraped and generated data is stored in the `/data` directory as CSV and TXT files.
- **Market Analysis:** Uses LLMs to analyze product data and generate deep market insights.
- **Q&A Chatbot:** Users can ask questions about the latest analysis and get AI-generated answers.
- **Business Report Generation:** Produces executive-ready business reports from the analysis.
- **Job Management:** Tracks scraping, analysis, and report jobs with status and history.
- **Modern Frontend:** Responsive dashboard, scraping controls, analysis viewer, Q&A chat, and report download.

---

## Directory Structure

```
multi_agent/
  agents/
    agent_scraper.py         # Playwright-based scraping logic
    agent_analysis.py        # Product data analysis using LLMs
    qa_chatbot.py            # Q&A chatbot using latest analysis
    report_generator.py      # Business report generation
  data/
    all_products.csv         # Latest combined product data
    breakout_products.csv    # Breakout-only data
    rastah_products.csv      # Rastah-only data
    deep_analysis.txt        # Latest analysis output
    generated_report.txt     # Latest business report
    ...                     # Other run-specific files
  frontend/
    templates/               # Jinja2 HTML templates (dashboard, scraper, analysis, etc.)
    static/js/               # Frontend JS (scraper, analysis, Q&A, auth, etc.)
  main.py                    # FastAPI backend entrypoint
  requirements.txt           # Python dependencies
```

---

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install Playwright browsers:
   ```bash
   playwright install
   ```
3. Create a `.env` file in the root directory with:
   ```
   GROQ_API_KEY=your_groq_api_key
   ```
4. Run the app:
   ```bash
   uvicorn main:app --reload
   ```
5. Visit [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## Usage

- Register and log in via the web UI.
- All API endpoints (except login/register) require authentication.
- Scrape data via the Scraper page. Data is saved as `/data/all_products.csv` and per-source CSVs.
- Run analysis via the Analysis page. Output is saved as `/data/deep_analysis.txt`.
- Use the Q&A Bot to ask questions about the latest analysis.
- Generate and download business reports via the Reports page. Output is saved as `/data/generated_report.txt`.
- View all your jobs and their status in the History page.

---

## API Endpoints

- `POST /register` — Register a new user
- `POST /token` — Login and get JWT token
- `POST /start-scrape` — Start scraping, returns CSV file
- `POST /api/scraper/start` — Start scraping as a job (returns job_id)
- `GET /api/scraper/status/{job_id}` — Get scraping job status
- `GET /api/scraper/download/{job_id}` — Download zipped CSVs for a job
- `POST /api/analyze` — Run market analysis as a job
- `POST /api/qa` — Ask a question about the latest analysis
- `POST /api/generate-report` — Generate a business report
- `GET /api/report-latest` — Get the latest generated report
- `GET /api/history` — List all jobs for the current user

---

## Data Files

- `all_products.csv` — Combined product data from all sources
- `breakout_products.csv`, `rastah_products.csv` — Source-specific data
- `deep_analysis.txt` — Latest market analysis
- `generated_report.txt` — Latest business report
