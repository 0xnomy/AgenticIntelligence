from typing import TypedDict, List, Optional, Dict, cast, Annotated, Sequence
import os
import csv
from datetime import datetime
import traceback
import operator
import asyncio

from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

# Import existing agents
from .agent_scraper import scrape_breakout, scrape_rastah, save_to_csv
from .agent_analysis import run_deep_analysis
from .qa_chatbot import qa_chatbot
from .report_generator import generate_report

# Improved PipelineState
class PipelineState(TypedDict):
    question: str
    max_products: int
    headless: bool
    scraped_data: Dict[str, List[List[str]]]
    analysis_results: str
    report: Optional[str]
    messages: Annotated[list, add_messages]
    progress_status: str
    progress_log: List[str]
    status: str  # 'pending', 'running', 'failed', 'completed'
    error: Optional[str]

def log_progress(state: PipelineState, message: str) -> None:
    timestamp = datetime.now().isoformat()
    state["progress_log"].append(f"[{timestamp}] {message}")

async def scraper_agent(state: PipelineState) -> PipelineState:
    try:
        state["progress_status"] = "scraping"
        log_progress(state, "Starting scraping step...")
        # Check if data already exists
        breakout_path = "data/breakout_products.csv"
        rastah_path = "data/rastah_products.csv"
        if os.path.exists(breakout_path) and os.path.exists(rastah_path):
            log_progress(state, "Scraped data already exists. Skipping scraping.")
            with open(breakout_path, newline='', encoding='utf-8') as f:
                breakout_data = list(csv.reader(f))[1:]
            with open(rastah_path, newline='', encoding='utf-8') as f:
                rastah_data = list(csv.reader(f))[1:]
            return {
                **state,
                "scraped_data": {
                    "breakout": breakout_data,
                    "rastah": rastah_data
                },
                "messages": [{
                    "role": "system",
                    "content": f"Skipped scraping. Loaded {len(breakout_data)} Breakout and {len(rastah_data)} Rastah products from CSV."
                }]
            }
        # Scrape data from both sources (async)
        breakout_data, rastah_data = await asyncio.gather(
            scrape_breakout(max_products=state["max_products"]//2, headless=state["headless"]),
            scrape_rastah(max_products=state["max_products"]//2, headless=state["headless"])
        )
        save_to_csv(breakout_data, breakout_path)
        save_to_csv(rastah_data, rastah_path)
        log_progress(state, f"Scraping complete. {len(breakout_data)} Breakout, {len(rastah_data)} Rastah products.")
        return {
            **state,
            "scraped_data": {
                "breakout": breakout_data,
                "rastah": rastah_data
            },
            "messages": [{
                "role": "system",
                "content": f"Completed scraping. Found {len(breakout_data)} Breakout products and {len(rastah_data)} Rastah products"
            }]
        }
    except Exception as e:
        error_msg = f"Scraper agent error: {str(e)}\n{traceback.format_exc()}"
        log_progress(state, error_msg)
        return {**state, "error": error_msg, "status": "failed"}

async def analysis_agent(state: PipelineState) -> PipelineState:
    try:
        state["progress_status"] = "analyzing"
        log_progress(state, "Starting analysis step...")
        # Check if analysis already exists
        analysis_path = "data/deep_analysis.txt"
        if os.path.exists(analysis_path):
            with open(analysis_path, "r", encoding="utf-8") as f:
                analysis_results = f.read()
            log_progress(state, "Analysis already exists. Skipping analysis.")
            return {
                **state,
                "analysis_results": analysis_results,
                "messages": [{
                    "role": "system",
                    "content": "Skipped analysis. Loaded existing analysis results."
                }]
            }
        # Run analysis
        run_deep_analysis("data/breakout_products.csv", "data/rastah_products.csv")
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis_results = f.read()
        log_progress(state, "Analysis complete.")
        return {
            **state,
            "analysis_results": analysis_results,
            "messages": [{
                "role": "system", 
                "content": "Completed deep analysis of product data"
            }]
        }
    except Exception as e:
        error_msg = f"Analysis agent error: {str(e)}\n{traceback.format_exc()}"
        log_progress(state, error_msg)
        return {**state, "error": error_msg, "status": "failed"}

async def qa_agent(state: PipelineState) -> PipelineState:
    try:
        state["progress_status"] = "qa_processing"
        log_progress(state, "Starting QA step...")
        answer_question = qa_chatbot()
        answer = answer_question(state["question"])
        log_progress(state, "QA complete.")
        return {
            **state,
            "messages": [{
                "role": "assistant",
                "content": answer
            }]
        }
    except Exception as e:
        error_msg = f"QA agent error: {str(e)}\n{traceback.format_exc()}"
        log_progress(state, error_msg)
        return {**state, "error": error_msg, "status": "failed"}

async def report_agent(state: PipelineState) -> PipelineState:
    try:
        state["progress_status"] = "generating_report"
        log_progress(state, "Starting report generation step...")
        report_path = "data/generated_report.txt"
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report_content = f.read()
            log_progress(state, "Report already exists. Skipping generation.")
            return {
                **state,
                "report": report_content,
                "progress_status": "completed",
                "messages": [{
                    "role": "system",
                    "content": "Skipped report generation. Loaded existing report."
                }]
            }
        generate_report()
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
        log_progress(state, "Report generation complete.")
        return {
            **state,
            "report": report_content,
            "progress_status": "completed",
            "messages": [{
                "role": "system",
                "content": "Report generation completed"
            }]
        }
    except Exception as e:
        error_msg = f"Report agent error: {str(e)}\n{traceback.format_exc()}"
        log_progress(state, error_msg)
        return {**state, "error": error_msg, "status": "failed"}

def route_next(state: PipelineState) -> str:
    if state.get("error"):
        return "end"
    if not state.get("scraped_data"):
        return "scraper"
    if not state.get("analysis_results"):
        return "analyzer" 
    if not state.get("report"):
        return "report"
    return "end"

class Pipeline:
    def __init__(self):
        self.graph = StateGraph(PipelineState)
        self.graph.add_node("scraper", scraper_agent)
        self.graph.add_node("analyzer", analysis_agent) 
        self.graph.add_node("qa", qa_agent)
        self.graph.add_node("report", report_agent)
        self.graph.add_conditional_edges(
            "scraper",
            route_next,
            {
                "analyzer": "analyzer",
                "end": "end"
            }
        )
        self.graph.add_conditional_edges(
            "analyzer", 
            route_next,
            {
                "qa": "qa",
                "end": "end"
            }
        )
        self.graph.add_conditional_edges(
            "qa",
            route_next,
            {
                "report": "report",
                "end": "end"
            }
        )
        self.graph.add_conditional_edges(
            "report",
            route_next,
            {
                "end": "end"
            }
        )
        self.graph.set_entry_point("scraper")

    async def invoke(self, state: PipelineState) -> PipelineState:
        app = self.graph.compile()
        return await app.ainvoke(state)

# Create pipeline instance
app = Pipeline() 