"""
Langfuse tracing wrapper. If Langfuse keys aren't set, this is a no-op passthrough
so the app still runs without observability configured.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import LANGFUSE_ENABLED, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST

if LANGFUSE_ENABLED:
    # Langfuse Python SDK v3+: the callback handler no longer takes
    # public_key/secret_key/host as constructor args — it reads them from
    # LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST in os.environ,
    # which config.py's load_dotenv() call already populated.
    from langfuse.langchain import CallbackHandler

    langfuse_handler = CallbackHandler()

    def get_config():
        return {"callbacks": [langfuse_handler]}
else:
    def get_config():
        return {}


def invoke_traced(graph, inputs: dict):
    """Invoke the compiled LangGraph with Langfuse tracing attached if configured."""
    return graph.invoke(inputs, config=get_config())
