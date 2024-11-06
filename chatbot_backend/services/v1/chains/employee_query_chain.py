import os
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores.neo4j_vector import Neo4jVector
from langchain.prompts import (
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)

employee_details_chat_template_str = """
Your job is to use the provided employee data to answer 
questions about their roles, performance, and experiences 
within the company. Use the following context to answer questions. 
Be as detailed as possible, but don't make up any information that's 
not from the context. If you don't know an answer, say you don't know.

Context:
{context}

Your answer should be in a JSON format with the following keys:

    "Answer": "The answer to the question.",
    "Context": Context
    
Helpful Answer:
"""

employee_details_chat_system_prompt = SystemMessagePromptTemplate(
    prompt=PromptTemplate(
        input_variables=["context"],
        template=employee_details_chat_template_str
    )
)

human_prompt = HumanMessagePromptTemplate(
    prompt=PromptTemplate(
        input_variables=["question"],
        template="Can you provide details on: {question}?"
    )
)

messages = [employee_details_chat_system_prompt, human_prompt]


qa_prompt = ChatPromptTemplate(
    messages=messages,
    input_variables=["context", "question"]
)

llm = ChatOpenAI(model="gpt-3.5-turbo")


# It will create the index if it doesn't exist
neo4j_graph_vector_index = Neo4jVector.from_existing_graph(
    embedding=OpenAIEmbeddings(),
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    index_name="employee",
    node_label="Employee",
    text_node_properties=[
        "address",
        "notes",
        "city",
        "postalCode",
        "title",
        "firstName",
        "lastName",
        "region",
    ],
    embedding_node_property="embedding",
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=neo4j_graph_vector_index.as_retriever(),
    # ['stuff', 'map_reduce', 'refine', 'map_rerank']
    chain_type="stuff",
)

qa_chain.combine_documents_chain.llm_chain.prompt = qa_prompt
