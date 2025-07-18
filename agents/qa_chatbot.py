import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pydantic import SecretStr
from pathlib import Path

load_dotenv()

def qa_chatbot():
    # Load the latest analysis context every time
    analysis_path = Path(__file__).parent.parent / 'data' / 'deep_analysis.txt'
    if not analysis_path.exists():
        print(f"[QA Chatbot] File not found: {analysis_path}")
        return lambda question: "No analysis report found. Please run the market analysis first."
    with open(analysis_path, 'r', encoding='utf-8') as f:
        analysis_context = f.read().strip()
    print(f"[QA Chatbot] Loaded analysis context from: {analysis_path} ({len(analysis_context)} characters)")

    # Initialize the chat model
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    model = ChatGroq(
        api_key=SecretStr(GROQ_API_KEY or ""),
        model="moonshotai/kimi-k2-instruct",
        temperature=0.2,
    )

    def answer_question(question: str) -> str:
        prompt = (
            f"You are a market research assistant. Use ONLY the following analysis as context to answer the user's question. "
            f"If the answer is not in the analysis, say 'The analysis does not provide information on that.'\n"
            f"Respond in a professional, direct, and confident manner.\n"
            f"Analysis Context:\n{analysis_context}\n\n"
            f"User Question: {question}\n"
            f"Answer:"
        )
        print(f"[QA Chatbot] Prompt sent to LLM (length: {len(prompt)} characters)")
        response = model.invoke(prompt)
        # Extract only the reply text, always cast to str before strip
        if hasattr(response, "content"):
            result = str(response.content).strip()
        elif hasattr(response, "text"):
            result = str(response.text).strip()
        elif isinstance(response, dict) and "content" in response:
            result = str(response["content"]).strip()
        elif isinstance(response, str):
            result = response.strip()
        else:
            result = str(response).strip()
        print(f"[QA Chatbot] LLM response: {result}")
        return result

    return answer_question
