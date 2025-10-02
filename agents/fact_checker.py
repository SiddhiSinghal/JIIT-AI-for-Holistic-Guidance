# agents/fact_checker.py
from dotenv import load_dotenv
import os
from langchain_community.chat_models import ChatOllama
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from datetime import datetime

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "mistral")
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

class FactCheckResult(BaseModel):
    verdict: str               # True / False / Uncertain
    confidence: float          # Between 0 and 1
    explanation: str
    sources: list[str]

parser = PydanticOutputParser(pydantic_object=FactCheckResult)
llm = ChatOllama(model=LLM_MODEL)

# Tools
search_tool = SerpAPIWrapper(serpapi_api_key=SERPAPI_KEY)
wiki_api = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=2000)
wiki_tool = WikipediaQueryRun(api_wrapper=wiki_api)

def fact_check(claim: str):
    """Fact-check a single claim. Returns structured result (FactCheckResult) or error dict."""
    print(f"\n🔎 Fact-checking: {claim}")

    try:
        web_result = search_tool.run(claim)
    except Exception as e:
        print("⚠️ SerpAPI Error:", e)
        web_result = f"Search failed: {e}"

    try:
        wiki_result = wiki_tool.run(claim)
    except Exception as e:
        print("⚠️ Wikipedia Error:", e)
        wiki_result = f"Wikipedia lookup failed: {e}"

    prompt = f"""
Claim: "{claim}"

Search Results:
{web_result}

Wikipedia Result:
{wiki_result}

Your job is to verify whether the above claim is true or false based on the evidence. If evidence is insufficient, mark it as "Uncertain".

Respond ONLY in this JSON format:
{parser.get_format_instructions()}
"""

    response = llm.invoke(prompt)

    try:
        # result = parser.parse(response)
        result = parser.parse(response.content)

        # Save to file
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("fact_check_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- {timestamp} ---\nClaim: {claim}\nResult: {result}\n\n")

        return result

    except Exception as e:
        print("❌ Failed to parse response.", e)
        return {"error": str(e), "raw_response": response.content}
