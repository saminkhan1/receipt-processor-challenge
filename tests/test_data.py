from typing import List, Dict, Any

VALID_RECEIPTS: List[Dict[str, Any]] = [
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:01",
        "items": [{"shortDescription": "Mountain-Dew", "price": "6.49"}],
        "total": "6.49",
    }
]

INVALID_RECEIPTS: List[Dict[str, Any]] = [
    {
        "retailer": "Target!!!",  # Invalid characters
        "purchaseDate": "2022-01-02",
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Pepsi - 12-oz", "price": "1.25"}],
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-02",
        # Missing purchaseTime
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}],
    },
    {
        "retailer": "Target",
        "purchaseDate": "01-02-2022",  # Wrong format
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}],
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-02",
        "purchaseTime": "1:13 PM",  # Wrong format
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}],
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-02",
        "purchaseTime": "13:13",
        "total": "1.255",  # Wrong format
        "items": [{"shortDescription": "Item", "price": "1.25"}],
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-02",
        "purchaseTime": "13:13",
        "total": "0.00",
        "items": [],  # Empty list
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-13-01",  # Invalid month
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "Target",
        "purchaseTime": "25:00",  # Invalid hour
        "purchaseDate": "2022-01-01",
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "Target",
        "purchaseTime": "13:13",
        "purchaseDate": "2022-01-01",
        "total": "1.2",  # Invalid price format
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "Target$Store",  # $ not allowed in pattern
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "Target/Store",  # / not allowed in pattern
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:13",
        "total": "1.2",  # Doesn't match ^\d+\.\d{2}$
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": ".25"}]  # Missing leading digit
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Item@123", "price": "1.25"}]  # @ not allowed in ^[\w\s\-]+$
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Item/123", "price": "1.25"}]  # / not allowed
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "24:00",  # Invalid hour
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "23:60",  # Invalid minute
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022/01/01",  # Wrong separator
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-13-01",  # Invalid month
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "",  # Empty retailer
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [{"shortDescription": "Item", "price": "1.25"}]
    },
    {
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": []  # Empty items list
    }
]

POINTS_TEST_CASES: List[Dict[str, Any]] = [
    {
        "receipt": {
            "retailer": "Target",  # 6 alphanumeric chars = 6 points
            "purchaseDate": "2022-01-01",  # Odd day = 6 points
            "purchaseTime": "13:01",  # Not between 2-4 PM = 0 points
            "items": [
                {
                    "shortDescription": "Mountain Dew",  # Length 11 (not multiple of 3) = 0 points
                    "price": "6.49"  # Not used for points since description length not multiple of 3
                }
            ],
            "total": "6.49"  # Not round dollar (0 points), not multiple of 0.25 (0 points)
        },
        "expected_points": 14  # 6 (retailer) + 6 (odd day) + 2 (one pair of items rounded up)
    },
    {
        "receipt": {
            "retailer": "M&M Corner Market",  # 14 alphanumeric chars (excluding &) = 14 points
            "purchaseDate": "2023-03-15",  # Odd day = 6 points
            "purchaseTime": "14:30",  # Between 2-4 PM = 10 points
            "total": "100.00",  # Round dollar (50) + multiple of 0.25 (25) = 75 points
            "items": [
                {
                    "shortDescription": "ABC",  # Length 3 (multiple of 3)
                    "price": "50.00"  # 50.00 * 0.2 = 10 points
                },
                {
                    "shortDescription": "DEF",  # Length 3 (multiple of 3)
                    "price": "50.00"  # 50.00 * 0.2 = 10 points
                }
            ]
        },
        "expected_points": 130  # Fixed the expected points
    },
    {
        "receipt": {
            "retailer": "X",
            "purchaseDate": "2022-02-02",  # Even day
            "purchaseTime": "12:00",  # Not between 2-4 PM
            "total": "5.99",  # Not round, not multiple of 0.25
            "items": [{"shortDescription": "Item 1234", "price": "5.99"}],  # Length not multiple of 3
        },
        "expected_points": 3,  # 1 (retailer) + 2 (rounded up from 5.99 * 0.2)
    },
    {
        "receipt": {
            "retailer": "Target",
            "purchaseDate": "2022-01-01",
            "purchaseTime": "14:01",
            "items": [
                {"shortDescription": "Item One", "price": "10.00"},
                {"shortDescription": "Item Two", "price": "10.00"},
                {"shortDescription": "Item Three", "price": "10.00"},
                {"shortDescription": "Item Four", "price": "10.00"}
            ],
            "total": "40.00",
        },
        "expected_points": 109  # 6 (retailer) + 6 (odd day) + 10 (time) + 50 (round) + 25 (0.25) + 10 (4 items) + 2 (Item Three length=9)
    },
    {
        "receipt": {
            "retailer": "ABC123",
            "purchaseDate": "2023-03-15",
            "purchaseTime": "15:00",
            "total": "12.25",
            "items": [
                {"shortDescription": "ABC", "price": "6.00"},
                {"shortDescription": "DEF", "price": "6.25"}
            ]
        },
        "expected_points": 56  # 6 (retailer) + 6 (odd day) + 10 (time) + 25 (0.25) + 5 (2 items) + 4 (descriptions)
    },
    {
        "receipt": {
            "retailer": "Super Store",
            "purchaseDate": "2023-03-16",  # Even day
            "purchaseTime": "16:01",  # After 2-4 PM
            "total": "15.00",  # Round dollar
            "items": [
                {"shortDescription": "ABCD", "price": "7.50"},  # Length = 4
                {"shortDescription": "EFGH", "price": "7.50"}   # Length = 4
            ]
        },
        "expected_points": 90  # 10 (retailer) + 50 (round dollar) + 25 (0.25) + 5 (2 items)
    },
    {
        "receipt": {
            "retailer": "Target Store",  # 11 alphanumeric chars
            "purchaseDate": "2023-03-15",  # Odd day
            "purchaseTime": "14:30",  # Between 2-4 PM
            "total": "35.25",  # Multiple of 0.25
            "items": [
                {"shortDescription": "ABC", "price": "10.00"},  # Length multiple of 3
                {"shortDescription": "DEFG", "price": "5.00"},  # Length not multiple of 3
                {"shortDescription": "XYZ", "price": "20.25"}   # Length multiple of 3
            ]
        },
        "expected_points": 64  # 11 (retailer) + 6 (odd day) + 10 (time) + 25 (0.25) + 5 (2 items) + 7 (descriptions: ceil(10.00 * 0.2) + ceil(20.25 * 0.2))
    }
]

# Update VALID_TEST_RECEIPT to match api.yml patterns exactly
VALID_TEST_RECEIPT = {
    "retailer": "Target",  # Matches ^[\w\s\-&]+$
    "purchaseDate": "2022-01-01",
    "purchaseTime": "13:01",
    "items": [
        {
            "shortDescription": "Mountain Dew",  # Matches ^[\w\s\-]+$
            "price": "6.49"  # Matches ^\d+\.\d{2}$
        }
    ],
    "total": "6.49"  # Matches ^\d+\.\d{2}$
}
