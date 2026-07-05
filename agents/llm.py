"""
Shared LLM client used by all agent nodes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE

llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    api_key=OPENAI_API_KEY,
)
