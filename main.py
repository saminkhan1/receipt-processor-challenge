from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from models import Receipt, ReceiptResponse, PointsResponse, ReceiptData
from receipt_processor import ReceiptProcessor
from typing import Annotated
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from cachetools import TTLCache
from datetime import timedelta
from functools import lru_cache

# Configure logging with a more efficient format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s|%(levelname)s|%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Constants in a config class for better organization
class Config:
    CORS_ORIGINS = ["*"]
    CACHE_TTL = timedelta(hours=24)
    CACHE_MAXSIZE = 1000


# Create a TTL cache for receipts
receipts_cache = TTLCache(
    maxsize=Config.CACHE_MAXSIZE, ttl=Config.CACHE_TTL.total_seconds()
)


@lru_cache()
def get_receipt_processor():
    """Cache the receipt processor instance"""
    return ReceiptProcessor()


async def get_validated_receipt(receipt: Receipt) -> Receipt:
    """Dependency for receipt validation"""
    if receipt.retailer.strip() != receipt.retailer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid receipt format",
        )

    for item in receipt.items:
        if item.shortDescription.strip() != item.shortDescription:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid receipt format",
            )

    return receipt


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting Receipt Processor API")
        yield
    finally:
        logger.info("Shutting down Receipt Processor API")
        receipts_cache.clear()


app = FastAPI(
    title="Receipt Processor",
    description="A service for processing receipts and calculating points",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom exception handler for validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid receipt format"},
    )


@app.get("/")
async def root():
    """Root endpoint returning API information"""
    return {"message": "Receipt Processor API"}


@app.post(
    "/receipts/process",
    response_model=ReceiptResponse,
    responses={
        400: {"description": "Invalid receipt"},
        422: {"description": "Validation Error"},
    },
    tags=["receipts"],
)
async def process_receipt(
    receipt: Annotated[Receipt, Depends(get_validated_receipt)],
) -> ReceiptResponse:
    """Process a receipt and return an ID"""
    try:
        receipt_id = str(uuid.uuid4())
        processor = get_receipt_processor()
        points = processor.calculate_points(receipt)
        receipts_cache[receipt_id] = ReceiptData(receipt=receipt, points=points)

        logger.info(f"Processed receipt {receipt_id}: {points} points")
        return ReceiptResponse(id=receipt_id)

    except Exception as e:
        logger.error(f"Error processing receipt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid receipt format",
        )


@app.get(
    "/receipts/{id}/points",
    response_model=PointsResponse,
    responses={404: {"description": "Receipt not found"}},
    tags=["receipts"],
)
async def get_points(id: str) -> PointsResponse:
    """Retrieve points for a receipt by ID"""
    receipt_data = receipts_cache.get(id)
    if not receipt_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Receipt not found", "id": id},
        )

    logger.info(f"Retrieved {receipt_data.points} points for receipt {id}")
    return PointsResponse(points=receipt_data.points)


def main():
    """Entry point for running the application"""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
