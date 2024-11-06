from langchain.tools import tool

from services.v1.chains.cypher_query_chain import (
    cypher_chain
)


@tool("general-qa-tool", return_direct=True)
def general_qa_tool(query: str) -> str:
    """Useful for answering general questions about orders, order details, shipper, customers, and products."""
    response = cypher_chain.invoke(query)

    return response.get("result")
