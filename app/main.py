from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

from app.routes.asl_ws import router as asl_router  # import the correct router
from app.routes.asl_http import router as asl_http_router

# Configure logging with detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('backend.log')
    ]
)
logger = logging.getLogger("app")
logger.info("NewSight ASL Backend starting...")

app = FastAPI()

# Allow all origins for development; tighten in production
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/health")
async def health_check():
	return {"status": "ok"}


# Include the ASL WebSocket router
app.include_router(asl_router)
# Include the ASL HTTP image upload router
app.include_router(asl_http_router)
