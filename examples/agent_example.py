"""
Decodo + LlamaIndex Agent Example
==================================

Demonstrates building a ReAct agent backed by the Decodo Web Scraping API.
The agent can browse live URLs and run web searches to answer questions.

Prerequisites
-------------
pip install llama-index-tools-decodo llama-index-llms-openai

Environment variables
---------------------
DECODO_API_TOKEN  — your Decodo API token
OPENAI_API_KEY    — your OpenAI API key (used for the LLM)

Run
---
python examples/agent_example.py
"""

import asyncio
import os

from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.settings import Settings
from llama_index.llms.openai import OpenAI
from llama_index.tools.decodo import DecodoToolSpec

# ---------------------------------------------------------------------------
# 1. Configure the LLM
# ---------------------------------------------------------------------------

Settings.llm = OpenAI(
    model="gpt-4o",
    api_key=os.environ["OPENAI_API_KEY"],
)

# ---------------------------------------------------------------------------
# 2. Build the Decodo tool spec and convert to LlamaIndex tools
# ---------------------------------------------------------------------------

spec = DecodoToolSpec(api_token=os.environ["DECODO_API_TOKEN"])

tools = spec.to_tool_list()

print("Registered tools:")
for tool in tools:
    print(f"  - {tool.metadata.name}: {tool.metadata.description[:80]}...")

# ---------------------------------------------------------------------------
# 3. Create the agent
# ---------------------------------------------------------------------------

agent = ReActAgent(tools=tools, llm=Settings.llm)

# ---------------------------------------------------------------------------
# 4. Run example queries
# ---------------------------------------------------------------------------

QUERIES = [
    "What are the top stories on Hacker News right now? Summarise the top 3.",
    "Search Google for 'best Python web frameworks 2025' and tell me which "
    "frameworks appear most frequently in the results.",
    "Go to https://docs.python.org/3/library/asyncio.html and give me a "
    "one-paragraph summary of what asyncio does.",
]

async def main() -> None:
    for query in QUERIES:
        print("\n" + "=" * 70)
        print(f"QUERY: {query}")
        print("=" * 70)
        response = await agent.run(query)
        print(f"\nANSWER:\n{response}")


asyncio.run(main())
