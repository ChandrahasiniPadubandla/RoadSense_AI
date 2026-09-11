
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.chatbot.config import GROQ_API_KEY, GROQ_MODEL
from app.chatbot.prompts import SYSTEM_PROMPT
from app.chatbot.tools import ALL_TOOLS

_executor: AgentExecutor | None = None


def get_agent_executor() -> AgentExecutor:
    """Build the agent once and reuse it (the LLM client + tool bindings are
    stateless and safe to share across requests; per-conversation state is
    passed in explicitly at invoke() time instead)."""
    global _executor
    if _executor is not None:
        return _executor

    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to backend/.env — see .env.example."
        )

    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)
    _executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=False,
        max_iterations=6,
        handle_parsing_errors=True,
    )
    return _executor
