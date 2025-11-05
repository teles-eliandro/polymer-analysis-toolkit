
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.molecular import router as molecular_router

app = FastAPI(
    title="Polymer Analysis Toolkit (PAT) - API",
    description="RESTful API for polymer molecular analysis (Mn, Mw, Đ).",
    version="0.1.0",
)

# CORS: permita o domínio do seu frontend no Vercel!
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",            # dev local
        "https://polymer-analysis-toolkit.vercel.app",  # substitua pelo seu domínio do Vercel!
        "https://seu-frontend.vercel.app"   # ou use ["*"] temporariamente (não recomendado para produção)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(molecular_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to Polymer Analysis Toolkit (PAT) API!"}
