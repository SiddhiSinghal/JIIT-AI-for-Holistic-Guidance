# agents/web_researcher.py
from dotenv import load_dotenv
import os
from pydantic import BaseModel
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import PydanticOutputParser
from .tools import search_tool, wiki_tool, save_to_txt
from datetime import datetime

load_dotenv()

# model name configurable
LLM_MODEL = os.getenv("LLM_MODEL", "mistral")

class ResearchRespone(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]

parser = PydanticOutputParser(pydantic_object=ResearchRespone)
llm = ChatOllama(model=LLM_MODEL)

def run_research(query: str):
    """Return parsed structured research response and save to file."""
    print(f"\n🔍 Running research for: {query}")

    try:
        search_result = search_tool.run(query)
    except Exception as e:
        search_result = f"Search failed: {e}"
        print("⚠️ Search error:", e)

    try:
        wiki_result = wiki_tool.run(query)
    except Exception as e:
        wiki_result = f"Wikipedia lookup failed: {e}"
        print("⚠️ Wikipedia error:", e)

    tool_output = f"""
The user asked: {query}

Search Results:
{search_result}

Wikipedia Result:
{wiki_result}

You used the following tools: search, wikipedia, save_text_to_file.

Now generate a structured research response using this data.

Respond in this format:
{parser.get_format_instructions()}
"""

    response = llm.invoke(tool_output)

    try:
        # structured = parser.parse(response)
        structured = parser.parse(response.content)

        # Save structured output to file
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_to_txt(f"Query: {query}\n\nSearch Result:\n{search_result}\n\nWikipedia:\n{wiki_result}\n\nStructured:\n{structured}\n", filename="final_research_output.txt")
        print("\n📁 Research saved to 'final_research_output.txt'")

        return structured

    except Exception as e:
        print("❌ Failed to parse response.", e)
        return {"error": str(e), "raw_response": response.content}
