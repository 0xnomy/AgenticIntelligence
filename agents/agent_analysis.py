import os
import csv
from typing import List, Dict, Optional
from pydantic import SecretStr
from langchain_groq import ChatGroq
from langchain.schema import AIMessage
import glob
from pathlib import Path
import re

from dotenv import load_dotenv
load_dotenv()

# Set your Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set")

# Define the LLM using Groq's model
llm = ChatGroq(
    api_key=SecretStr(GROQ_API_KEY),
    model="deepseek-r1-distill-llama-70b",
    temperature=0.2,
)

def get_latest_csv_files() -> List[str]:
    """Get the latest all_products CSV file by modification time or size, or fallback to separate source files."""
    data_dir = Path('data')
    all_products_files = list(data_dir.glob('all_products_*.csv'))
    if all_products_files:
        # Sort by modification time (descending), then by size (descending)
        all_products_files.sort(key=lambda f: (f.stat().st_mtime, f.stat().st_size), reverse=True)
        latest_file = str(all_products_files[0])
        print(f"Using latest combined products file: {latest_file}")
        return [latest_file]
    # Fallback to separate source files
    breakout_files = list(data_dir.glob('breakout_products_*.csv'))
    rastah_files = list(data_dir.glob('rastah_products_*.csv'))
    if not (breakout_files or rastah_files):
        raise ValueError(
            "No product data files found. Please run the scraper first to collect data. "
            "Go to the Scraper page and click 'Start Scraping' to gather product information."
        )
    files_to_analyze = []
    if breakout_files:
        breakout_files.sort(key=lambda f: (f.stat().st_mtime, f.stat().st_size), reverse=True)
        latest_breakout = str(breakout_files[0])
        files_to_analyze.append(latest_breakout)
        print(f"Using Breakout products file: {latest_breakout}")
    if rastah_files:
        rastah_files.sort(key=lambda f: (f.stat().st_mtime, f.stat().st_size), reverse=True)
        latest_rastah = str(rastah_files[0])
        files_to_analyze.append(latest_rastah)
        print(f"Using Rastah products file: {latest_rastah}")
    return files_to_analyze

def load_csv_products(file_paths: List[str]) -> List[Dict]:
    """Load and validate product data from CSV files"""
    all_products = []
    for file_path in file_paths:
        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                products = [row for row in reader]
                if not products:
                    raise ValueError(
                        f"The file {Path(file_path).name} exists but contains no product data. "
                        "This might indicate an issue with the scraping process. "
                        "Try running the scraper again to collect fresh data."
                    )
                print(f"Loaded {len(products)} products from {Path(file_path).name}")
                all_products.extend(products)
        except FileNotFoundError:
            raise ValueError(
                f"Could not find the file {Path(file_path).name}. "
                "The data file might have been moved or deleted. "
                "Please run the scraper again to generate new data files."
            )
        except csv.Error:
            raise ValueError(
                f"Error reading {Path(file_path).name}. "
                "The file appears to be corrupted or in an incorrect format. "
                "Try running the scraper again to generate fresh data files."
            )
    if not all_products:
        raise ValueError(
            "No product data found in any of the files. "
            "This might indicate an issue with the scraping process. "
            "Please try running the scraper again with different parameters."
        )
    print(f"Total products loaded: {len(all_products)}")
    return all_products

def clean_llm_output(text: str) -> str:
    """Remove <think>...</think> and any internal reasoning from LLM output."""
    # Remove <think>...</think> blocks
    text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
    # Remove any leading/trailing whitespace and extra blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text

def analyze_products(file_paths: Optional[List[str]] = None) -> str:
    """Analyze products from CSV files and return analysis"""
    try:
        print("\nStarting market analysis...")
        # If no file paths provided, get the latest ones
        paths_to_analyze = file_paths if file_paths is not None else get_latest_csv_files()
        print(f"Files to analyze: {paths_to_analyze}")
        products = load_csv_products(paths_to_analyze)
        if len(products) < 2:
            raise ValueError(
                "Not enough product data for meaningful analysis. "
                f"Found only {len(products)} product(s). "
                "Please run the scraper to collect more product data."
            )
        print(f"Analyzing {len(products)} products...")
        prompt = (
            "You are a market research analyst. Given the following product data from multiple e-commerce sites, "
            "perform a deep analysis including: internal product comparison, cross-site comparison, market research, and trend identification. "
            "Be thorough and analytical.\n\n"
            "Product Data:\n"
        )
        for product in products:
            prompt += f"- Name: {product.get('Product', '')}\n  Price: {product.get('Price', '')}\n  Description: {product.get('Description', '')}\n"
        prompt += ("\nYour analysis should include:\n"
                   "- Comparison of products (features, price, uniqueness) across all sites\n"
                   "- Identification of market trends\n"
                   "- Insights about product positioning and opportunities\n"
                   "- Any notable patterns or outliers\n"
                   "Provide a detailed, structured report.")
        print("Generating analysis with AI model...")
        try:
            response = llm.invoke(prompt)
        except Exception as e:
            raise ValueError(
                "Error during analysis with the AI model. "
                "This might be due to API limits or connectivity issues. "
                f"Technical details: {str(e)}"
            )
        # Extract only the text content from the response
        if isinstance(response, AIMessage):
            result = response.content
        elif isinstance(response, dict) and "content" in response:
            result = response["content"]
        elif isinstance(response, str):
            result = response
        else:
            result = str(response)
        # Clean the output to remove internal reasoning
        result = clean_llm_output(str(result))
        # Save to file
        try:
            data_dir = Path('data')
            output_file = data_dir / "deep_analysis.txt"
            with open(output_file, "w", encoding='utf-8') as f:
                f.write(str(result))
            print(f"Analysis saved to: {output_file}")
        except Exception as e:
            raise ValueError(
                "Error saving analysis results to file. "
                "Please check if the data directory exists and is writable. "
                f"Technical details: {str(e)}"
            )
        print("Analysis completed successfully!")
        return str(result)
    except ValueError as e:
        # Re-raise ValueError with the same message
        raise
    except Exception as e:
        error_msg = (
            "An unexpected error occurred during analysis. "
            "This might be due to system issues or invalid data. "
            f"Technical details: {str(e)}"
        )
        print(error_msg)
        raise ValueError(error_msg)

def run_deep_analysis(*csv_paths: str) -> str:
    """Run deep analysis on CSV files and save results"""
    try:
        paths_list = list(csv_paths) if csv_paths else None
        analysis = analyze_products(paths_list)
        print("\n===== Deep Product Analysis Report =====\n")
        print(analysis)
        return analysis
    except Exception as e:
        error_msg = (
            "Failed to complete the analysis process. "
            f"Error: {str(e)}"
        )
        print(error_msg)
        raise ValueError(error_msg)

if __name__ == "__main__":
    run_deep_analysis()