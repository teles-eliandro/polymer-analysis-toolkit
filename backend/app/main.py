
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.molecular import router as molecular_router

app = FastAPI(
    title="Polymer Analysis Toolkit (PAT) - API",
    version="0.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # para desenvolvimento local
        "https://polymer-analysis-toolkit.vercel.app",  # produção
        "https://polymer-analysis-toolkit-dpwlj9509-eliandros-projects-c60477e2.vercel.app", # preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(molecular_router, prefix="/api/v1")  # ← este prefixo é crucial!

@app.get("/")
def root():
    return {"message": "PAT API is running!"}
