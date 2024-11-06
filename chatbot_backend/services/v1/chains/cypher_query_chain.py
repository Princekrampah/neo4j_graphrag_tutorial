import os
from langchain_community.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD")
)

graph.refresh_schema()

cypher_generation_template_str = """
Task:
Generate Cypher query for a Neo4j graph database.

Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.

Schema:
{schema}

Note:
Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything other than
for you to construct a Cypher statement. Do not include any text except
the generated Cypher statement. Make sure the direction of the relationship is
correct in your queries. Make sure you alias both entities and relationships
properly. Do not run any queries that would add to or delete from
the database. Make sure to alias all statements that follow as with
statement (e.g. WITH c as customer, o.orderID as order_id).
If you need to divide numbers, make sure to
filter the denominator to be non-zero.

Examples:
# Retrieve the total number of orders placed by each customer.
MATCH (c:Customer)-[o:ORDERED_BY]->(order:Order)
RETURN c.customerID AS customer_id, COUNT(o) AS total_orders

# List the top 5 products with the highest unit price.
MATCH (p:Product)
RETURN p.productName AS product_name, p.unitPrice AS unit_price
ORDER BY unit_price DESC
LIMIT 5

# Find all employees who have processed orders.
MATCH (e:Employee)-[r:PROCESSED_BY]->(o:Order)
RETURN e.employeeID AS employee_id, COUNT(o) AS orders_processed

# take a product, find out who ordered it and which shipping company shipped the order.
MATCH (s: Shipper)<-[sr: SHIPPED_BY ]-(o: Order{{orderID: 10249}})-[cr: ORDERED_BY]->(c: Customer)
RETURN s, sr, o, c, cr;

# Get all information about a given order, all its relationships and nodes connected to it.
MATCH (o: Order)-[r]-(n)
WHERE o.orderID = 10249
RETURN o, r, n;

# Get freight cost for each shippment to Germany by Speedy Express.
MATCH (s: Shipper)<-[sr: SHIPPED_BY]-(o: Order)-[i:INCLUDES]->(p: Product)
WHERE s.companyName = "Speedy Express" 
AND o.shipCountry = "Germany"
RETURN  COUNT(*) AS shpments_to_germany,
o.freight AS freight, p.productName AS product_name;

# Get sum of total freight cost for each order by Speedy Express in Germany.
MATCH (s: Shipper)<-[sr: SHIPPED_BY]-(o: Order)-[i:INCLUDES]->(p: Product)
WHERE s.companyName = "Speedy Express" 
AND o.shipCountry = "Germany"
RETURN  COUNT(*) AS shpments_to_germany,
SUM(o.freight) AS freight;



String category values:
Use existing strings and values from the schema provided. 

The question is:
{question}
"""


cypher_generation_prompt = PromptTemplate(
    input_variables=["schema", "question"], template=cypher_generation_template_str
)

qa_generation_template_str = """
You are an assistant that takes the results from a Neo4j Cypher query and forms a human-readable response. The query results section contains the results of a Cypher query that was generated based on a user's natural language question. The provided information is authoritative; you must never question it or use your internal knowledge to alter it. Make the answer sound like a response to the question.

Query Results:
{context}

Question:
{question}

If the provided information is empty, respond by stating that you don't know the answer. Empty information is indicated by: []

If the information is not empty, you must provide an answer using the results. If the question involves a time duration, assume the query results are in units of days unless specified otherwise.

When names are provided in the queary results, such as hospital names, be cautious of any names containing commas or other punctuation. For example, 'Jones, Brown and Murray' is a single hospital name, not multiple hospitals. Ensure that any list of names is presented clearly to avoid ambiguity and make the full names easily identifiable.

Never state that you lack sufficient information if data is present in the query results. Always utilize the data provided.

Your answer should be in a JSON format with the following keys:

    "Answer": "The answer to the question.",
    "Context": Query Results

Helpful Answer:
"""


qa_generation_prompt = PromptTemplate(
    input_variables=["context", "question"], template=qa_generation_template_str
)

cypher_chain = GraphCypherQAChain.from_llm(
    top_k=100,
    graph=graph,
    verbose=True,
    validate_cypher=True,
    qa_prompt=qa_generation_prompt,
    cypher_prompt=cypher_generation_prompt,
    qa_llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0),
    cypher_llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0),
    allow_dangerous_requests=True,
)
