from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic.v1 import SecretStr
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

app = FastAPI()

# CORS setup (allow all for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve ai-plugin.json and openapi.json from .well-known
app.mount(
    "/.well-known",
    StaticFiles(directory="static/well-known"),
    name="well-known"
)

# In-memory storage
memory_store = []
tasks_store = []
task_id_counter = 1

# ----------- Models -----------

class PromptRequest(BaseModel):
    prompt: str

class MemoryItem(BaseModel):
    text: str

class Task(BaseModel):
    id: int | None = None
    title: str
    completed: bool = False

# ----------- Auth Helper -----------

def verify_api_key(request: Request):
    api_key = request.headers.get("x-api-key")
    expected_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

# ----------- Routes -----------

@app.get("/openapi.json")
async def serve_openapi():
    return FileResponse("static/well-known/openapi.json")

@app.post("/ask")
async def ask(request: Request, body: PromptRequest):
    verify_api_key(request)

    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        api_key=SecretStr(os.getenv("OPENAI_API_KEY") or "")
    )

    prompt = ChatPromptTemplate.from_template("You are a helpful assistant. {input}")
    chain = prompt | llm

    result = chain.invoke({"input": body.prompt})
    return {"response": result.content}

@app.get("/memory")
async def get_memory(request: Request):
    verify_api_key(request)
    return {"memory": memory_store}

@app.post("/memory")
async def add_memory(request: Request, item: MemoryItem):
    verify_api_key(request)
    memory_store.append(item.text)
    return {"message": "Memory item added"}

@app.get("/tasks")
async def get_tasks(request: Request):
    verify_api_key(request)
    return {"tasks": tasks_store}

@app.post("/tasks")
async def create_task(request: Request, task: Task):
    global task_id_counter
    verify_api_key(request)
    task.id = task_id_counter
    tasks_store.append(task)
    task_id_counter += 1
    return {"message": "Task created", "task": task}

@app.patch("/tasks/{task_id}")
async def update_task(task_id: int, request: Request, updated_task: Task):
    verify_api_key(request)
    for i, task in enumerate(tasks_store):
        if task.id == task_id:
            tasks_store[i] = Task(id=task_id, title=updated_task.title, completed=updated_task.completed)
            return {"message": "Task updated", "task": tasks_store[i]}
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int, request: Request):
    verify_api_key(request)
    for i, task in enumerate(tasks_store):
        if task.id == task_id:
            tasks_store.pop(i)
            return {"message": "Task deleted"}
    raise HTTPException(status_code=404, detail="Task not found")
