from typing import Optional, List

from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from memory import MemoryType
from memory_redis import retrieve_memories

@tool
def retrieve_memories_tool(
    query: str,
    memory_type: List[MemoryType],
    limit: int = 5,
    config: Optional[RunnableConfig] = None,
) -> str:
    """
    Retrieve long-term memories relevant to the query.

    Use this tool to access previously stored information about user
    preferences, experiences, or general knowledge.
    """
    config = config or RunnableConfig()
    user_id = config.get("user_id", "system")

    try:
        # Get long-term memories
        stored_memories = retrieve_memories(
            query=query,
            memory_type=memory_type,
            user_id=user_id,
            limit=limit,
            distance_threshold=0.3,
        )

        # Format the response
        response = []

        if stored_memories:
            response.append("Long-term memories:")
            for memory in stored_memories:
                response.append(f"- [{memory.memory_type}] {memory.content}")

        return "\n".join(response) if response else "No relevant memories found."

    except Exception as e:
        return f"Error retrieving memories: {str(e)}"
    
# result = retrieve_memories_tool.invoke({"query": "Airline preferences", "memory_type": ["episodic"]})
# print(result)