from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List
from pydantic import BaseModel, Field, model_validator, ConfigDict

# Constants from API spec
RETAILER_PATTERN = r"^[\w\s\-&]+$"  # Matches API spec exactly
DESC_PATTERN = r"^[\w\s\-]+$"  # Matches API spec exactly
PRICE_PATTERN = r"^\d+\.\d{2}$"  # Matches API spec exactly

class Item(BaseModel):
    """
    Item model as defined in API spec components.schemas.Item
    """
    model_config = ConfigDict(
        frozen=True,  # Immutable model
        str_strip_whitespace=True,  # Auto strip whitespace
        extra="forbid"  # Prevent extra fields
    )

    shortDescription: str = Field(
        ...,  # Required field
        pattern=DESC_PATTERN,
        description="The Short Product Description for the item.",
        examples=[
            "Mountain Dew 12PK",
            "Emils Cheese Pizza",
            "Knorr Creamy Chicken",
            "Doritos Nacho Cheese",
            "Klarbrunn 12-PK 12 FL OZ"
        ]
    )
    price: str = Field(
        ...,  # Required field
        pattern=PRICE_PATTERN, 
        description="The total price paid for this item.",
        examples=["6.49"]
    )

    @model_validator(mode='before')
    @classmethod
    def validate_price_value(cls, data: dict) -> dict:
        """Validate price is a valid decimal >= 0"""
        if not isinstance(data, dict):
            raise ValueError("Invalid item data")
            
        price = data.get('price')
        if price:
            try:
                value = Decimal(price)
                if value < 0:
                    raise ValueError("Price must be >= 0")
            except (ValueError, TypeError, InvalidOperation):
                raise ValueError("Invalid price format")
                
        return data

class Receipt(BaseModel):
    """
    Receipt model as defined in API spec components.schemas.Receipt
    """
    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
        extra="forbid"
    )

    retailer: str = Field(
        ...,
        pattern=RETAILER_PATTERN,
        description="The name of the retailer or store the receipt is from.",
        examples=[
            "Target",
            "M&M Corner Market"
        ]
    )
    purchaseDate: str = Field(
        ...,
        pattern=r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$",
        description="The date of the purchase printed on the receipt.",
        examples=["2022-01-01"]
    )
    purchaseTime: str = Field(
        ...,
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        description="The time of the purchase printed on the receipt. 24-hour time expected.",
        examples=["13:01"]
    )
    items: List[Item] = Field(
        ...,
        min_length=1,
        description="The items purchased."
    )
    total: str = Field(
        ...,
        pattern=PRICE_PATTERN,
        description="The total amount paid on the receipt.",
        examples=["6.49"]
    )

    @model_validator(mode='before')
    @classmethod
    def validate_receipt(cls, data: dict) -> dict:
        """Validate complete receipt data"""
        if not isinstance(data, dict):
            raise ValueError("Invalid receipt data")

        # Validate date/time format
        try:
            date = data.get('purchaseDate', '')
            time = data.get('purchaseTime', '')
            datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("Invalid date/time format")

        # Validate total is valid decimal >= 0
        total = data.get('total')
        if total:
            try:
                value = Decimal(total)
                if value < 0:
                    raise ValueError("Total must be >= 0")
            except (ValueError, TypeError, InvalidOperation):
                raise ValueError("Invalid total format")

        return data

class ReceiptResponse(BaseModel):
    """
    Response model for /receipts/process endpoint
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    id: str = Field(
        ...,
        pattern=r"^\S+$",
        description="The ID assigned to the processed receipt",
        examples=["7fb1377b-b223-49d9-a31a-5a02701dd310"]
    )

class PointsResponse(BaseModel):
    """
    Response model for /receipts/{id}/points endpoint
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    points: int = Field(
        ...,
        ge=0,
        description="The points awarded for the receipt",
        examples=[32]
    )

class ReceiptData(BaseModel):
    """
    Internal model for storing receipt data with points
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    receipt: Receipt
    points: int = Field(..., ge=0)
