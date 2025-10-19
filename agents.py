from langchain_core.messages import AIMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.prebuilt.chat_agent_executor import create_react_agent
from langgraph.checkpoint.redis import RedisSaver
from langchain_core.runnables.config import RunnableConfig

from memory_redis import redis_client
from store_tool import store_memory_tool
from retrieve_tool import retrieve_memories_tool
import logging

logger = logging.getLogger(__name__)
# Set up the Redis checkpointer for short term memory
redis_saver = RedisSaver(redis_client=redis_client)
redis_saver.setup()

tools = [store_memory_tool, retrieve_memories_tool]

llm = ChatOllama(model="qwen3:4b", temperature=0.7).bind_tools(tools=tools)

# Defint the travel agent
travel_agent = create_react_agent(
    model=llm,
    tools=tools,               # Long-term memory: provided as a set of custom tools
    checkpointer=redis_saver,  # Short-term memory: the conversation history
    prompt=SystemMessage(
        content="""
        您是一位旅行助手，帮助用户规划旅行。您会记住用户的偏好，并根据以往的互动提供个性化的推荐。

        您可访问以下类型的记忆：

        短期记忆：当前对话内容
        长期记忆：
        体验性记忆：用户的偏好和过往旅行经历（例如：“用户偏爱靠窗座位”）
        语义性记忆：关于旅游目的地及出行要求的一般知识
        您具备过程性知识（如如何搜索、预订航班等），这些知识已集成在您的工具和提示中。

        请始终以友好、个性化且符合上下文的方式提供帮助。
        """
    ),
)

from langchain_core.messages import HumanMessage
from langgraph.graph.message import MessagesState


class RuntimeState(MessagesState):
    """Runtime state for the travel agent."""
    pass


def respond_to_user(state: RuntimeState, config: RunnableConfig) -> RuntimeState:
    """Invoke the travel agent to generate a response."""
    human_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not human_messages:
        logger.warning("No HumanMessage found in state")
        return state

    try:
        # Single agent invocation, not streamed (simplified for reliability)
        result = travel_agent.invoke({"messages": state["messages"]}, config=config)
        agent_message = result["messages"][-1]
        state["messages"].append(agent_message)
    except Exception as e:
        logger.error(f"Error invoking travel agent: {e}")
        agent_message = AIMessage(
            content="I'm sorry, I encountered an error processing your request."
        )
        state["messages"].append(agent_message)

    return state

from langchain_core.messages import ToolMessage


def execute_tools(state: RuntimeState, config: RunnableConfig) -> RuntimeState:
    """Execute tools specified in the latest AIMessage and append ToolMessages."""
    messages = state["messages"]
    latest_ai_message = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage) and m.tool_calls),
        None
    )

    if not latest_ai_message:
        return state  # No tool calls to process

    tool_messages = []
    for tool_call in latest_ai_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        # Find the corresponding tool
        tool = next((t for t in tools if t.name == tool_name), None)
        if not tool:
            continue  # Skip if tool not found

        try:
            # Execute the tool with the provided arguments
            result = tool.invoke(tool_args, config=config)
            # Create a ToolMessage with the result
            tool_message = ToolMessage(
                content=str(result),
                tool_call_id=tool_id,
                name=tool_name
            )
            tool_messages.append(tool_message)
        except Exception as e:
            # Handle tool execution errors
            error_message = ToolMessage(
                content=f"Error executing tool '{tool_name}': {str(e)}",
                tool_call_id=tool_id,
                name=tool_name
            )
            tool_messages.append(error_message)

    # Append the ToolMessages to the message history
    messages.extend(tool_messages)
    state["messages"] = messages
    return state


from langchain_core.messages import RemoveMessage

# An LLM configured for summarization.
summarizer = ChatOllama(model="qwen3:4b", temperature=0.3)

# The number of messages after which we'll summarize the conversation.
MESSAGE_SUMMARIZATION_THRESHOLD = 6


def summarize_conversation(
    state: RuntimeState, config: RunnableConfig
) -> RuntimeState:
    """
    Summarize a list of messages into a concise summary to reduce context length
    while preserving important information.
    """
    messages = state["messages"]
    current_message_count = len(messages)
    if current_message_count < MESSAGE_SUMMARIZATION_THRESHOLD:
        logger.debug(f"Not summarizing conversation: {current_message_count}")
        return state

    system_prompt = """
        您是一位对话摘要生成器。请对用户与旅行助手之前的对话进行简洁总结。

        摘要应包含：

        关键话题、用户偏好和已做决定
        任何具体的旅行细节（如目的地、日期、偏好）
        尚待解决的问题或需后续跟进的内容
        内容简洁但信息完整
        请以简明叙述段落的形式呈现摘要。
    """

    message_content = "\n".join(
        [
            f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
            for msg in messages
        ]
    )

    # Invoke the summarizer
    summary_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=f"Please summarize this conversation:\n\n{message_content}"
        ),
    ]

    summary_response = summarizer.invoke(summary_messages)

    logger.info(f"Summarized {len(messages)} messages into a conversation summary")

    summary_message = SystemMessage(
        content=f"""
        Summary of the conversation so far:

        {summary_response.content}

        Please continue the conversation based on this summary and the recent messages.
        """
    )
    remove_messages = [
        RemoveMessage(id=msg.id) for msg in messages if msg.id is not None
    ]

    state["messages"] = [  # type: ignore
        *remove_messages,
        summary_message,
        state["messages"][-1],
    ]

    return state.copy()

from langgraph.graph import StateGraph, END

workflow = StateGraph(RuntimeState)

# Add nodes to the graph
workflow.add_node("agent", respond_to_user)
workflow.add_node("execute_tools", execute_tools)
workflow.add_node("summarize_conversation", summarize_conversation)

def decide_next_step(state):
    latest_ai_message = next((m for m in reversed(state["messages"]) if isinstance(m, AIMessage)), None)
    if latest_ai_message and latest_ai_message.tool_calls:
        return "execute_tools"
    return "summarize_conversation"


workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    decide_next_step,
    {"execute_tools": "execute_tools", "summarize_conversation": "summarize_conversation"},
)
workflow.add_edge("execute_tools", "agent")
workflow.add_edge("summarize_conversation", END)


graph = workflow.compile(checkpointer=redis_saver)

def main(thread_id: str = "book_flight", user_id: str = "demo_user"):
    """Main interaction loop for the travel agent"""

    print("Welcome to the Travel Assistant! (Type 'exit' to quit)")

    config = RunnableConfig(configurable={"thread_id": thread_id, "user_id": user_id})
    state = RuntimeState(messages=[])

    while True:
        user_input = input("\nYou (type 'quit' to quit): ")

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            print("Thank you for using the Travel Assistant. Goodbye!")
            break

        state["messages"].append(HumanMessage(content=user_input))

        try:
            # Process user input through the graph
            for result in graph.stream(state, config=config, stream_mode="values"):
                state = RuntimeState(**result)

            logger.debug(f"# of messages after run: {len(state['messages'])}")

            # Find the most recent AI message, so we can print the response
            ai_messages = [m for m in state["messages"] if isinstance(m, AIMessage)]
            if ai_messages:
                message = ai_messages[-1].content
            else:
                logger.error("No AI messages after run")
                message = "I'm sorry, I couldn't process your request properly."
                # Add the error message to the state
                state["messages"].append(AIMessage(content=message))

            print(f"\nAssistant: {message}")

        except Exception as e:
            logger.exception(f"Error processing request: {e}")
            error_message = "I'm sorry, I encountered an error processing your request."
            print(f"\nAssistant: {error_message}")
            # Add the error message to the state
            state["messages"].append(AIMessage(content=error_message))

# NBVAL_SKIP

try:
    user_id = input("Enter a user ID: ") or "demo_user"
    thread_id = input("Enter a thread ID: ") or "demo_thread"
except Exception:
    # If we're running in CI, we don't have a terminal to input from, so just exit
    exit()
else:
    main(thread_id, user_id)