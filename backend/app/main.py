from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.molecular import router as molecular_router

app = FastAPI(
    title="Polymer Analysis Toolkit (PAT) - API",
    description="RESTful API for polymer molecular analysis (Mn, Mw, Đ).",
    version="0.1.0",
)

# CORS para permitir frontend em localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(molecular_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to Polymer Analysis Toolkit (PAT) API!"}