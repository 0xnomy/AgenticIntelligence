import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

def generate_report() -> str:
    """
    Loads the deep analysis, generates a comprehensive business report using a Groq LLM, and saves it to data/generated_report.txt.
    Returns the generated report as a string.
    """
    # Paths
    analysis_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'deep_analysis.txt')
    report_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'generated_report.txt')

    # Load analysis content
    try:
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis_content = f.read().strip()
    except FileNotFoundError:
        print(f"Error: {analysis_path} not found.")
        return "Analysis file not found. Please run market analysis first."
    except Exception as e:
        print(f"Error reading analysis file: {e}")
        return f"Error reading analysis file: {e}"

    # Initialize the chat model
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    model = ChatGroq(
        api_key=SecretStr(GROQ_API_KEY or ""),
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        temperature=0.3,
    )

    # Improved system prompt for a visually appealing business report
    system_prompt = (
        "You are a senior business analyst. Based on the following market analysis, generate a comprehensive business report. "
        "The report should be well-structured, visually appealing, and suitable for presentation to executives. "
        "Use clear section headings, bullet points, and concise language. Include:\n"
        "- Executive Summary\n"
        "- Key Findings (with bullet points)\n"
        "- Market Trends\n"
        "- Product Positioning & Opportunities\n"
        "- Notable Patterns & Outliers\n"
        "- Actionable Recommendations\n"
        "- Conclusion\n"
        "Format the report for easy reading. Use bold for section titles and bullet points for lists."
    )

    # Compose the full prompt
    prompt = f"{system_prompt}\n\nMarket Analysis Data:\n{analysis_content}\n\nWrite the business report below:"

    # Generate the report
    try:
        response = model.invoke(prompt)
        if hasattr(response, "content"):
            report = str(response.content).strip()
        elif hasattr(response, "text"):
            report = str(response.text).strip()
        elif isinstance(response, dict) and "content" in response:
            report = str(response["content"]).strip()
        elif isinstance(response, str):
            report = response.strip()
        else:
            report = str(response).strip()
    except Exception as e:
        print(f"Error generating report: {e}")
        return f"Error generating report: {e}"

    # Save the report
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report successfully saved to {report_path}")
    except Exception as e:
        print(f"Error saving report: {e}")
        return f"Error saving report: {e}"

    return report

if __name__ == "__main__":
    print(generate_report())