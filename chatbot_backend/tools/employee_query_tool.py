from langchain.tools import tool

from services.v1.chains.employee_query_chain import (
    qa_chain as employee_query_chain
)


@tool("employee-qa-tool", return_direct=True)
def employee_qa_tool(query: str) -> str:
    """Useful for answering questions about employees who work at a company."""
    response = employee_query_chain.invoke(query)

    return response.get("result")
