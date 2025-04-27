from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.correlation import CorrelationMiddleware
from app.config.logging import init_logging
from app.api.routes import router

# Initialize logging
init_logging()

# Create FastAPI app with minimal configuration
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

# Add middleware
app.add_middleware(CorrelationMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Simple test endpoint without any middleware or complex logging
@app.get("/test")
async def test_endpoint():
    return {"message": "Test successful"}
