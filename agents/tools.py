# agents/tools.py
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import WikipediaQueryRun
from langchain.tools import Tool
from datetime import datetime
import os

# expects SERPAPI_API_KEY in env
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

# SerpAPI wrapper (search)
search_tool = SerpAPIWrapper(serpapi_api_key=SERPAPI_KEY)

# Wikipedia
wiki_api = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=2000)
wiki_query = WikipediaQueryRun(api_wrapper=wiki_api)
wiki_tool = wiki_query

# Save tool
def save_to_txt(data: str, filename: str = "research_output.txt") -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"--- Research Output --- \nTimestamp: {timestamp}\n\n{data}\n\n"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(formatted_text)
    return f"✅ Data successfully saved to {filename}"
