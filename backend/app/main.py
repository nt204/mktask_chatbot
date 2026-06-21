from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import projects, tasks, status, chat, documents

app = FastAPI(title="AI PM Copilot API", version="1.0.0")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to AI PM Copilot API"}

from app.db.database import get_db
from fastapi import Depends
from psycopg2.extras import RealDictCursor

@app.get("/api/users")
def get_all_users(db=Depends(get_db)):
    cur = db.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT id, full_name, email, global_role FROM users ORDER BY global_role")
        return cur.fetchall()
    finally:
        cur.close()
