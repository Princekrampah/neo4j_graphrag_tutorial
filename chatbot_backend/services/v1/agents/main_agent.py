from langchain import hub
from langchain.agents import (
    AgentExecutor,
    create_tool_calling_agent
)
from langchain_openai import ChatOpenAI
from tools import employee_qa_tool, general_qa_tool

agent_prompt = hub.pull("hwchase17/openai-functions-agent")

tools = [employee_qa_tool, general_qa_tool]

# Create LLM
llm = ChatOpenAI(model="gpt-3.5-turbo")

# Construct the tool calling agent
agent = create_tool_calling_agent(llm, tools, agent_prompt)

# Create an agent executor by passing in the agent and tools
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,
    return_intermediate_steps=True
)
