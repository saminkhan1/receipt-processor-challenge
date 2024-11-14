import pytest
from typing import Dict, Any
from httpx import AsyncClient
from fastapi.testclient import TestClient
from main import app
from tests.test_data import (
    VALID_RECEIPTS,
    INVALID_RECEIPTS,
    POINTS_TEST_CASES,
    VALID_TEST_RECEIPT,
)
import asyncio

# Keep sync client for non-async tests
client = TestClient(app)


class TestReceiptProcessor:
    def test_root(self, client: TestClient) -> None:
        """Test root endpoint returns expected message"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Receipt Processor API"}

    @pytest.mark.parametrize("receipt", VALID_RECEIPTS)
    def test_process_valid_receipt(
        self, client: TestClient, receipt: Dict[str, Any]
    ) -> None:
        """Test processing valid receipts"""
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        assert "id" in response.json()

    @pytest.mark.parametrize("receipt", INVALID_RECEIPTS)
    def test_process_invalid_receipt(
        self, client: TestClient, receipt: Dict[str, Any]
    ) -> None:
        """Test processing invalid receipts returns 400 or 422"""
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code in [400, 422]

    def test_points_rules(self, client: TestClient) -> None:
        """Test each individual points rule"""
        rules_tests = [
            # Rule 1: One point for every alphanumeric character in the retailer name
            {
                "receipt": {
                    "retailer": "Target123",  # 8 alphanumeric chars = 8 points
                    "purchaseDate": "2022-01-02",
                    "purchaseTime": "13:13",
                    "total": "1.00",
                    "items": [{"shortDescription": "Item", "price": "1.00"}],
                },
                "min_points": 8,  # At least 8 points from retailer name
            },
            # Rule 2: 50 points if the total is a round dollar amount
            {
                "receipt": {
                    "retailer": "X",
                    "purchaseDate": "2022-01-02",
                    "purchaseTime": "13:13",
                    "total": "100.00",
                    "items": [{"shortDescription": "Item", "price": "100.00"}],
                },
                "min_points": 50,  # At least 50 points from round dollar
            },
        ]

        for test in rules_tests:
            response = client.post("/receipts/process", json=test["receipt"])
            assert response.status_code == 200
            receipt_id = response.json()["id"]

            points_response = client.get(f"/receipts/{receipt_id}/points")
            assert points_response.status_code == 200
            points_data = points_response.json()
            assert points_data["points"] >= test["min_points"]

    @pytest.mark.anyio
    async def test_retailer_with_ampersand(self, async_client: AsyncClient) -> None:
        """Test retailer names containing '&' are accepted and scored correctly"""
        receipt = {
            "retailer": "M&M Corner Market",
            "purchaseDate": "2022-01-02",
            "purchaseTime": "13:13",
            "total": "1.25",
            "items": [{"shortDescription": "Pepsi - 12-oz", "price": "1.25"}],
        }
        response = await async_client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = await async_client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        points_data = points_response.json()
        assert points_data["points"] > 0

    @pytest.mark.anyio
    async def test_boundary_purchase_times(self, async_client: AsyncClient) -> None:
        """Test boundary cases for the 2:00-4:00 PM time bonus"""
        receipt_at_2pm = {
            "retailer": "Target",
            "purchaseDate": "2022-01-02",
            "purchaseTime": "14:00",  # 2:00 PM
            "total": "1.25",
            "items": [{"shortDescription": "Item", "price": "1.25"}],
        }
        response = await async_client.post("/receipts/process", json=receipt_at_2pm)
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = await async_client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        points_data = points_response.json()
        assert points_data["points"] >= 10  # Should include time bonus

    @pytest.mark.anyio
    async def test_multiple_point_rules(self, async_client: AsyncClient) -> None:
        """Test receipt that qualifies for multiple point rules"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": "2023-01-01",  # Odd day
            "purchaseTime": "15:00",  # Between 2-4 PM
            "total": "10.00",  # Round dollar AND multiple of 0.25
            "items": [
                {"shortDescription": "ABC", "price": "5.00"},  # Length multiple of 3
                {"shortDescription": "DEF", "price": "5.00"},  # Length multiple of 3
            ],
        }
        response = await async_client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = await async_client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        points_data = points_response.json()
        assert points_data["points"] >= 75  # Should include multiple bonuses

    def test_invalid_receipt_id(self, client: TestClient) -> None:
        """Test requesting points for non-existent receipt ID returns 404"""
        response = client.get("/receipts/invalid-id/points")
        assert response.status_code == 404
        assert "Receipt not found" in response.json()["detail"]["message"]

    @pytest.mark.parametrize(
        "total,expected_min_points",
        [
            ("100.00", 75),  # Round dollar (50) + multiple of 0.25 (25)
            ("99.75", 25),  # Multiple of 0.25 only
            ("99.99", 0),  # Neither round nor multiple of 0.25
        ],
    )
    def test_total_amount_rules(
        self, client: TestClient, total: str, expected_min_points: int
    ) -> None:
        """Test points calculation for different total amounts"""
        receipt = {
            "retailer": "X",
            "purchaseDate": "2022-01-02",
            "purchaseTime": "13:13",
            "total": total,
            "items": [{"shortDescription": "Item", "price": total}],
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        assert points_response.json()["points"] >= expected_min_points

    @pytest.mark.parametrize(
        "num_items,expected_points",
        [
            (2, 5),  # 5 points for 2 items
            (4, 10),  # 10 points for 4 items
            (5, 10),  # 10 points for 5 items (2 pairs)
            (1, 0),  # No points for 1 item
        ],
    )
    def test_items_count_points(
        self, client: TestClient, num_items: int, expected_points: int
    ) -> None:
        """Test points calculation for different numbers of items"""
        items = [
            {"shortDescription": f"Item {i}", "price": "1.00"} for i in range(num_items)
        ]
        receipt = {
            "retailer": "X",
            "purchaseDate": "2022-01-02",
            "purchaseTime": "13:13",
            "total": f"{num_items}.00",
            "items": items,
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        assert points_response.json()["points"] >= expected_points

    @pytest.mark.parametrize(
        "description,price,expected_points",
        [
            ("ABC", "1.00", 1),  # Length 3, price * 0.2 = 0.2, rounded up to 1
            ("ABCD", "1.00", 0),  # Length 4, no points
            ("ABCDEF", "2.50", 1),  # Length 6, price * 0.2 = 0.5, rounded up to 1
        ],
    )
    def test_description_length_points(
        self, client: TestClient, description: str, price: str, expected_points: int
    ) -> None:
        """Test points calculation for item description lengths"""
        receipt = {
            "retailer": "X",
            "purchaseDate": "2022-01-02",
            "purchaseTime": "13:13",
            "total": price,
            "items": [{"shortDescription": description, "price": price}],
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        assert points_response.json()["points"] >= expected_points

    @pytest.mark.parametrize(
        "purchase_time,should_get_bonus",
        [
            ("13:59", False),  # Just before 2:00 PM
            ("14:00", True),  # Exactly 2:00 PM
            ("15:30", True),  # Middle of range
            ("16:00", False),  # Exactly 4:00 PM - should be FALSE per README
            ("16:01", False),  # Just after 4:00 PM
        ],
    )
    def test_time_range_points(
        self, client: TestClient, purchase_time: str, should_get_bonus: bool
    ) -> None:
        """Test points calculation for purchase time ranges"""
        # Use non-round number and even date to minimize other point rules
        receipt = {
            "retailer": "X",  # 1 point only for retailer
            "purchaseDate": "2022-01-02",  # Even day, no points
            "purchaseTime": purchase_time,
            "total": "1.23",  # Not round, not multiple of 0.25
            "items": [
                {"shortDescription": "Item", "price": "1.23"}
            ],  # Length not multiple of 3
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        points = points_response.json()["points"]
        base_points = 1  # Only from retailer name 'X'

        if should_get_bonus:
            assert points == base_points + 10  # Base points plus time bonus
        else:
            assert points == base_points  # Only base points, no time bonus

    @pytest.mark.parametrize(
        "invalid_receipt",
        [
            # Invalid retailer pattern
            {
                "retailer": "Target@Store",  # @ not allowed in pattern
                "purchaseDate": "2022-01-02",
                "purchaseTime": "13:13",
                "total": "1.25",
                "items": [{"shortDescription": "Item", "price": "1.25"}],
            },
            # Invalid date format
            {
                "retailer": "Target",
                "purchaseDate": "2022/01/02",  # Wrong separator
                "purchaseTime": "13:13",
                "total": "1.25",
                "items": [{"shortDescription": "Item", "price": "1.25"}],
            },
            # Invalid time format
            {
                "retailer": "Target",
                "purchaseDate": "2022-01-02",
                "purchaseTime": "1:13",  # Missing leading zero
                "total": "1.25",
                "items": [{"shortDescription": "Item", "price": "1.25"}],
            },
            # Invalid price pattern
            {
                "retailer": "Target",
                "purchaseDate": "2022-01-02",
                "purchaseTime": "13:13",
                "total": "1.2",  # Missing second decimal
                "items": [{"shortDescription": "Item", "price": "1.25"}],
            },
            # Invalid item description pattern
            {
                "retailer": "Target",
                "purchaseDate": "2022-01-02",
                "purchaseTime": "13:13",
                "total": "1.25",
                "items": [
                    {"shortDescription": "Item@123", "price": "1.25"}
                ],  # @ not allowed
            },
        ],
    )
    def test_schema_validation(
        self, client: TestClient, invalid_receipt: Dict[str, Any]
    ) -> None:
        """Test validation against OpenAPI schema patterns"""
        response = client.post("/receipts/process", json=invalid_receipt)
        assert response.status_code in [400, 422]  # Either validation error

    def test_total_matches_items(self, client: TestClient) -> None:
        """Test receipt where total doesn't match sum of items"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": "2022-01-02",
            "purchaseTime": "13:13",
            "total": "10.00",
            "items": [
                {"shortDescription": "Item 1", "price": "5.00"},
                {
                    "shortDescription": "Item 2",
                    "price": "4.00",
                },  # Sum = 9.00, not 10.00
            ],
        }
        response = client.post("/receipts/process", json=receipt)
        # The API spec doesn't explicitly require matching, but it's a good validation
        assert response.status_code in [
            200,
            400,
        ]  # Either accept or reject, but be consistent

    @pytest.mark.parametrize(
        "field", ["retailer", "purchaseDate", "purchaseTime", "items", "total"]
    )
    def test_missing_required_fields(self, client: TestClient, field: str) -> None:
        """Test that omitting required fields returns 422"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": "2022-01-02",
            "purchaseTime": "13:13",
            "total": "1.25",
            "items": [{"shortDescription": "Item", "price": "1.25"}],
        }
        del receipt[field]
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 422

    def test_item_description_edge_cases(self, client: TestClient) -> None:
        """Test edge cases for item descriptions"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": "2022-01-02",
            "purchaseTime": "13:13",
            "total": "2.00",
            "items": [
                {"shortDescription": "", "price": "1.00"},  # Empty description
                {
                    "shortDescription": "A" * 100,
                    "price": "1.00",
                },  # Very long description
            ],
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_concurrent_receipt_processing(self, async_client: AsyncClient) -> None:
        """Test processing multiple receipts concurrently"""
        receipt = VALID_RECEIPTS[0]
        tasks = [async_client.post("/receipts/process", json=receipt) for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # Check all succeeded and got unique IDs
        ids = set()
        for response in responses:
            assert response.status_code == 200
            receipt_id = response.json()["id"]
            assert receipt_id not in ids
            ids.add(receipt_id)

    @pytest.mark.parametrize(
        "invalid_date",
        [
            "2022-13-01",  # Invalid month
            "2022-00-01",  # Zero month
            "2022-01-32",  # Invalid day
            "2022-01-00",  # Zero day
        ],
    )
    def test_invalid_date_formats(self, client: TestClient, invalid_date: str) -> None:
        """Test invalid date formats are rejected"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": invalid_date,
            "purchaseTime": "13:13",
            "total": "1.25",
            "items": [{"shortDescription": "Item", "price": "1.25"}],
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code in [400, 422]  # Accept either validation error code

    @pytest.mark.parametrize(
        "invalid_time",
        [
            "24:00",  # Invalid hour
            "23:60",  # Invalid minute
            "13:1",  # Invalid format
            "1:30",  # Invalid format
            "13:13:13",  # Too many components
        ],
    )
    def test_invalid_time_formats(self, client: TestClient, invalid_time: str) -> None:
        """Test invalid time formats are rejected"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": "2022-01-01",
            "purchaseTime": invalid_time,
            "total": "1.25",
            "items": [{"shortDescription": "Item", "price": "1.25"}],
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code in [400, 422]  # Accept either validation error code

    def test_special_characters_in_descriptions(self, client: TestClient) -> None:
        """Test handling of special characters in item descriptions"""
        receipt = VALID_RECEIPTS[0].copy()
        receipt["items"] = [
            {"shortDescription": "Item@123", "price": "1.25"},  # @ character
            {"shortDescription": "Item#456", "price": "1.25"},  # # character
            {"shortDescription": "Item$789", "price": "1.25"},  # $ character
        ]
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code in [400, 422]

    def test_price_format_validation(self, client: TestClient) -> None:
        """Test various price format validations"""
        invalid_prices = [
            "1.2",  # Missing digit
            "1.234",  # Too many digits
            "1.",  # Missing decimals
            ".25",  # Missing leading zero
            "-1.25",  # Negative price
            "1,25",  # Wrong decimal separator
        ]

        for price in invalid_prices:
            receipt = VALID_RECEIPTS[0].copy()
            receipt["total"] = price
            receipt["items"][0]["price"] = price
            response = client.post("/receipts/process", json=receipt)
            assert response.status_code in [400, 422]

    @pytest.mark.parametrize("points_case", POINTS_TEST_CASES)
    def test_points_calculation(
        self, client: TestClient, points_case: Dict[str, Any]
    ) -> None:
        """Test points calculation for various scenarios"""
        response = client.post("/receipts/process", json=points_case["receipt"])
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        assert points_response.json()["points"] == points_case["expected_points"]

    def test_duplicate_receipt_ids(self, client: TestClient) -> None:
        """Test that each receipt gets a unique ID"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": "2022-01-01",
            "purchaseTime": "13:13",
            "total": "1.25",
            "items": [{"shortDescription": "Item", "price": "1.25"}],
        }
        ids = set()

        # Process the same receipt multiple times
        for _ in range(10):
            response = client.post("/receipts/process", json=receipt)
            assert response.status_code == 200
            receipt_id = response.json()["id"]
            assert receipt_id not in ids, "Duplicate receipt ID found"
            ids.add(receipt_id)

    def test_max_length_validation(self, client: TestClient) -> None:
        """Test maximum length validation for strings"""
        receipt = VALID_RECEIPTS[0].copy()
        receipt["retailer"] = "A" * 256  # Test very long retailer name
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code in [400, 422]

    def test_whitespace_handling(self, client: TestClient) -> None:
        """Test handling of leading/trailing whitespace"""
        receipt = VALID_RECEIPTS[0].copy()
        receipt["retailer"] = "  Target  "  # Leading/trailing spaces
        receipt["items"][0]["shortDescription"] = "  Item  "
        response = client.post("/receipts/process", json=receipt)
        # Should either trim whitespace or reject
        assert response.status_code in [200, 422]

    def test_item_price_validation(self, client: TestClient) -> None:
        r"""Test validation of item prices against api.yml pattern ^\d+\.\d{2}$"""
        receipt_template = {
            "retailer": "Target",
            "purchaseDate": "2022-01-01",
            "purchaseTime": "13:13",
            "items": [],
            "total": "0.00",
        }

        invalid_items = [
            {"shortDescription": "Item", "price": "0.0"},  # Missing decimal
            {"shortDescription": "Item", "price": "1.999"},  # Too many decimals
            {"shortDescription": "Item", "price": "1.0"},  # Missing decimal
            {"shortDescription": "Item", "price": ".25"},  # Missing leading digit
        ]

        for item in invalid_items:
            receipt = receipt_template.copy()
            receipt["items"] = [item]
            receipt["total"] = item["price"]
            response = client.post("/receipts/process", json=receipt)
            assert response.status_code in [
                400,
                422,
            ], f"Price {item['price']} should be invalid"

    @pytest.mark.parametrize(
        "retailer_name",
        [
            "Store!",  # Invalid special char
            "Store@123",  # Invalid special char
            "Store#Name",  # Invalid special char
            "",  # Empty string
            "   ",  # Only whitespace
        ],
    )
    def test_retailer_name_validation(
        self, client: TestClient, retailer_name: str
    ) -> None:
        r"""Test validation of retailer names against the pattern ^[\w\s\-&]+$"""
        receipt = VALID_RECEIPTS[0].copy()
        receipt["retailer"] = retailer_name
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code in [400, 422]

    @pytest.mark.parametrize(
        "purchase_time,expected_points",
        [
            ("13:59", 0),  # Just before 2:00 PM
            ("14:00", 10),  # Exactly 2:00 PM
            ("15:59", 10),  # Just before 4:00 PM
            ("16:00", 0),  # Exactly 4:00 PM
            ("16:01", 0),  # Just after 4:00 PM
        ],
    )
    def test_time_bonus_edge_cases(
        self, client: TestClient, purchase_time: str, expected_points: int
    ) -> None:
        """Test edge cases for time bonus points"""
        receipt = {
            "retailer": "X",  # Minimal retailer name
            "purchaseDate": "2022-01-02",  # Even day (no bonus)
            "purchaseTime": purchase_time,
            "total": "1.23",  # Not round, not multiple of 0.25
            "items": [{"shortDescription": "Item", "price": "1.23"}],
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        # Should only get points from retailer name (1) plus time bonus if applicable
        assert points_response.json()["points"] == 1 + expected_points

    def test_total_validation_edge_cases(self, client: TestClient) -> None:
        r"""Test edge cases for total validation according to api.yml pattern ^\d+\.\d{2}$"""
        edge_cases = [
            ("0.00", 200),  # Valid minimum
            ("0.25", 200),  # Valid minimum multiple of 0.25
            ("0.50", 200),  # Valid
            ("01.00", 200),  # Valid with leading zero per api.yml
            ("1.00", 200),  # Valid without leading zero
            ("99999.99", 200),  # Valid large number
            ("100000.00", 200),  # Valid large round number
            ("-0.00", 422),  # Invalid per api.yml pattern
            ("-1.00", 422),  # Invalid per api.yml pattern
            ("1.000", 422),  # Invalid per api.yml pattern
            ("1.0", 422),  # Invalid per api.yml pattern
            ("1.", 422),  # Invalid per api.yml pattern
            (".00", 422),  # Invalid per api.yml pattern
        ]

        for total, expected_status in edge_cases:
            receipt = {
                "retailer": "Test",
                "purchaseDate": "2022-01-01",
                "purchaseTime": "13:13",
                "items": [{"shortDescription": "Item", "price": "1.00"}],
                "total": total,
            }
            response = client.post("/receipts/process", json=receipt)
            assert response.status_code == expected_status, f"Failed for total: {total}"

    def test_description_length_points_2(self, client: TestClient) -> None:
        """Test points calculation for item description lengths"""
        receipt = {
            "retailer": "X",
            "purchaseDate": "2022-01-02",
            "purchaseTime": "13:13",
            "total": "35.00",
            "items": [
                {
                    "shortDescription": "ABC",
                    "price": "10.00",
                },  # Length 3: ceil(10.00 * 0.2) = 2
                {"shortDescription": "ABCD", "price": "10.00"},  # Length 4: 0
                {
                    "shortDescription": "ABCDEF",
                    "price": "10.00",
                },  # Length 6: ceil(10.00 * 0.2) = 2
                {
                    "shortDescription": " XYZ ",
                    "price": "5.00",
                },  # Trimmed length 3: ceil(5.00 * 0.2) = 1
            ],
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        points = points_response.json()["points"]

        # Calculate expected points:
        # 1 (retailer 'X')
        # + 50 (round dollar)
        # + 25 (multiple of 0.25)
        # + 10 (2 pairs of items)
        # + 5 (descriptions: ceil(10.00 * 0.2) + ceil(10.00 * 0.2) + ceil(5.00 * 0.2))
        expected_points = 91
        assert points == expected_points

    @pytest.mark.parametrize(
        "description,expected_status",
        [
            ("Valid-Item", 200),  # Valid with hyphen
            ("Valid Item", 200),  # Valid with space
            ("ValidItem123", 200),  # Valid with numbers
            ("Item@123", 422),  # Invalid per api.yml pattern
            ("Item#Description", 422),  # Invalid per api.yml pattern
            ("Item$100", 422),  # Invalid per api.yml pattern
            ("Item&Price", 422),  # Invalid per api.yml pattern
            ("", 422),  # Empty string
            (" ", 422),  # Only whitespace
        ],
    )
    def test_item_description_validation(
        self, client: TestClient, description: str, expected_status: int
    ) -> None:
        r"""Test validation of item descriptions against api.yml pattern ^[\w\s\-]+$"""
        receipt = {
            "retailer": "Test",
            "purchaseDate": "2022-01-01",
            "purchaseTime": "13:13",
            "total": "1.00",
            "items": [{"shortDescription": description, "price": "1.00"}],
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == expected_status

    def test_concurrent_points_calculation(self, client: TestClient) -> None:
        """Test concurrent points calculations for the same receipt"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": "2023-01-01",
            "purchaseTime": "15:00",
            "total": "100.00",
            "items": [{"shortDescription": "Item", "price": "100.00"}],
        }

        # Process same receipt multiple times
        response = client.post("/receipts/process", json=receipt)
        receipt_id = response.json()["id"]

        # Make concurrent requests for points
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(client.get, f"/receipts/{receipt_id}/points")
                for _ in range(20)
            ]

            # All requests should return same points
            expected_points = None
            for future in concurrent.futures.as_completed(futures):
                response = future.result()
                assert response.status_code == 200
                points = response.json()["points"]
                if expected_points is None:
                    expected_points = points
                else:
                    assert points == expected_points

    def test_error_response_format(self, client: TestClient) -> None:
        """Test error response format matches API spec"""
        # Test 404 format
        response = client.get("/receipts/invalid-id/points")
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert "message" in error_data["detail"]
        assert "id" in error_data["detail"]
        assert error_data["detail"]["message"] == "Receipt not found"

    def test_malformed_json(self, client: TestClient) -> None:
        """Test handling of malformed JSON requests"""
        response = client.post(
            "/receipts/process",
            headers={"Content-Type": "application/json"},
            content="invalid json{",
        )
        assert response.status_code == 422  # FastAPI returns 422 for invalid JSON

    def test_wrong_content_type(self, client: TestClient) -> None:
        """Test handling of wrong content type"""
        response = client.post(
            "/receipts/process",
            headers={"Content-Type": "text/plain"},
            content="not json",
        )
        assert response.status_code == 422  # FastAPI validates content type internally

    def test_unicode_characters(self, client: TestClient) -> None:
        """Test handling of unicode characters in strings"""
        receipt = VALID_RECEIPTS[0].copy()
        receipt["retailer"] = "Target™"  # Unicode trademark symbol
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 422  # Should reject non-pattern characters

    def test_large_receipt(self, client: TestClient) -> None:
        """Test processing of large receipts"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": "2022-01-01",
            "purchaseTime": "13:13",
            "total": "999999.99",
            "items": [
                {"shortDescription": f"Item{i}", "price": "1.00"}
                for i in range(1000)  # Large number of items
            ],
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "field,value",
        [
            ("retailer", None),
            ("purchaseDate", None),
            ("purchaseTime", None),
            ("total", None),
            ("items", None),
            ("shortDescription", None),
            ("price", None),
        ],
    )
    def test_null_values(self, client: TestClient, field: str, value: None) -> None:
        """Test handling of null values in JSON"""
        receipt = VALID_RECEIPTS[0].copy()
        if field in ["shortDescription", "price"]:
            receipt["items"][0][field] = value
        else:
            receipt[field] = value
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 422

    # Add test for root endpoint
    def test_root_endpoint(self, client: TestClient) -> None:
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Receipt Processor API"}

    # Add test for main function
    @staticmethod
    def test_main_function():
        """Test main function"""
        import main
        import uvicorn
        import unittest.mock as mock

        with mock.patch.object(uvicorn, "run") as mock_run:
            main.main()  # Call main() directly
            mock_run.assert_called_once_with(main.app, host="0.0.0.0", port=8000)

    @pytest.mark.parametrize("receipt_id", ["invalid-uuid", "123", "not-a-uuid", ""])
    def test_invalid_receipt_id_patterns(
        self, client: TestClient, receipt_id: str
    ) -> None:
        """Test invalid receipt ID formats against API spec pattern"""
        response = client.get(f"/receipts/{receipt_id}/points")
        assert response.status_code == 404

    def test_receipt_id_pattern(self, client: TestClient) -> None:
        """Test receipt ID matches pattern ^\\S+$ from API spec"""  # Fix escape sequence
        # Use a valid receipt that matches API spec patterns
        receipt = {
            "retailer": "Target",  # Must match ^[\w\s\-&]+$
            "purchaseDate": "2022-01-01",
            "purchaseTime": "13:01",
            "items": [
                {"shortDescription": "Item-1", "price": "1.00"}
            ],  # Must match ^[\w\s\-]+$
            "total": "1.00",
        }
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]
        assert " " not in receipt_id  # Verify no whitespace per pattern

    def test_points_calculation_edge_cases(self, client: TestClient) -> None:
        """Test edge cases for points calculation"""
        edge_cases = [
            {
                "receipt": {
                    "retailer": "Store",  # Valid retailer name (5 points)
                    "purchaseDate": "2022-01-01",  # Odd day (6 points)
                    "purchaseTime": "13:01",
                    "items": [{"shortDescription": "Item", "price": "1.00"}],
                    "total": "1.00",  # Round dollar (50 points) + multiple of 0.25 (25 points)
                },
                "expected_points": 86,  # 5 + 6 + 50 + 25
            },
            {
                "receipt": {
                    "retailer": "A-B-C",  # 3 alphanumeric chars
                    "purchaseDate": "2022-01-02",  # Even day
                    "purchaseTime": "13:01",
                    "items": [{"shortDescription": "Item", "price": "1.00"}],
                    "total": "1.00",
                },
                "expected_points": 78,  # 3 (retailer) + 50 (round dollar) + 25 (0.25 multiple)
            },
            {
                "receipt": {
                    "retailer": "Store",
                    "purchaseDate": "2022-01-01",  # Odd day
                    "purchaseTime": "14:00",  # Exactly 2:00 PM (gets bonus)
                    "items": [{"shortDescription": "Item", "price": "1.00"}],
                    "total": "1.00",
                },
                "expected_points": 96,  # 5 + 6 + 50 + 25 + 10
            },
            {
                "receipt": {
                    "retailer": "Store",
                    "purchaseDate": "2022-01-01",  # Odd day
                    "purchaseTime": "16:00",  # Exactly 4:00 PM (no bonus)
                    "items": [{"shortDescription": "Item", "price": "1.00"}],
                    "total": "1.00",
                },
                "expected_points": 86,  # 5 + 6 + 50 + 25
            },
        ]

        for case in edge_cases:
            response = client.post("/receipts/process", json=case["receipt"])
            assert response.status_code == 200
            receipt_id = response.json()["id"]

            points_response = client.get(f"/receipts/{receipt_id}/points")
            assert points_response.status_code == 200
            assert points_response.json()["points"] == case["expected_points"]

    def test_item_description_trimming(self, client: TestClient) -> None:
        """Test trimming of item descriptions for points calculation"""
        receipt = {
            "retailer": "Store",  # 5 points
            "purchaseDate": "2022-01-01",
            "purchaseTime": "13:01",
            "items": [
                {
                    "shortDescription": "   ABC   ",  # 3 chars after trim
                    "price": "10.00",  # ceil(10.00 * 0.2) = 2 points
                },
                {
                    "shortDescription": "\tDEF\n",  # 3 chars after trim
                    "price": "10.00",  # ceil(10.00 * 0.2) = 2 points
                },
            ],
            "total": "20.00",  # Round dollar (50) + multiple of 0.25 (25)
        }

        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]

        points_response = client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        # 5 (retailer) + 50 (round dollar) + 25 (multiple of 0.25) + 5 (2 items) + 4 (2 items with length 3 * price 0.2)
        assert points_response.json()["points"] == 95

    def test_response_format(self, client: TestClient) -> None:
        """Test response formats match API spec exactly"""
        # Test /receipts/process response
        process_response = client.post("/receipts/process", json=VALID_TEST_RECEIPT)
        assert process_response.status_code == 200
        process_data = process_response.json()
        assert list(process_data.keys()) == ["id"]
        assert isinstance(process_data["id"], str)

        # Test /receipts/{id}/points response
        points_response = client.get(f"/receipts/{process_data['id']}/points")
        assert points_response.status_code == 200
        points_data = points_response.json()
        assert list(points_data.keys()) == ["points"]
        assert isinstance(points_data["points"], int)


if __name__ == "__main__":
    pytest.main([__file__])
