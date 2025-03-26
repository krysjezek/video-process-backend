from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS (for development, allow all origins; for production, restrict as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change "*" to your frontend domain in production for better security.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your routers
from app.api.routes import router as api_router
app.include_router(api_router)

app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Hello World from FastAPI!"}
