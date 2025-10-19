from typing import Dict, Optional

from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from memory import MemoryType
from memory_redis import store_memory


@tool
def store_memory_tool(
    content: str,
    memory_type: MemoryType,
    metadata: Optional[Dict[str, str]] = None,
    config: Optional[RunnableConfig] = None,
) -> str:
    """
    Store a long-term memory in the system.

    Use this tool to save important information about user preferences,
    experiences, or general knowledge that might be useful in future
    interactions.
    """
    config = config or RunnableConfig()
    user_id = config.get("user_id", "system")
    thread_id = config.get("thread_id")

    try:
        # Store in long-term memory
        store_memory(
            content=content,
            memory_type=memory_type,
            user_id=user_id,
            thread_id=thread_id,
            metadata=str(metadata) if metadata else None,
        )

        return f"Successfully stored {memory_type} memory: {content}"
    except Exception as e:
        return f"Error storing memory: {str(e)}"
    
# store_memory_tool.invoke({"content": "I like flying on Delta when possible", "memory_type": "episodic"})