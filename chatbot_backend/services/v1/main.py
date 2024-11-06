from fastapi import FastAPI

from services.v1.agents.main_agent import agent_executor

app = FastAPI(
    title="Chatbot Backend",
    description="This is a simple chatbot backend",
)


@app.get("/")
def health_check():
    return {"Hello": "World this is code with prince"}


@app.post("/chat")
async def chat(query: str):
    response = await agent_executor.ainvoke({"input": query})

    intermediate_steps = [
        str(i_s) for i_s in response["intermediate_steps"]
    ]

    print(f"Intermediate steps: {intermediate_steps}")

    return {"response": response}
