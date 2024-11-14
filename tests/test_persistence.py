from typing import List, Dict, Any
import threading
import queue
from fastapi.testclient import TestClient
from tests.test_data import VALID_TEST_RECEIPT

class TestPersistence:
    def test_concurrent_modifications(self, client: TestClient) -> None:
        """Test concurrent modifications to in-memory storage"""
        errors = queue.Queue()
        
        def worker():
            try:
                receipt = {
                    "retailer": "Target",
                    "purchaseDate": "2022-01-01",
                    "purchaseTime": "13:01",
                    "items": [
                        {"shortDescription": "Mountain Dew", "price": "6.49"}
                    ],
                    "total": "6.49"
                }
                response = client.post("/receipts/process", json=receipt)
                assert response.status_code == 200
            except Exception as e:
                errors.put(e)
        
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}" 

    def test_receipt_persistence(self, client: TestClient) -> None:
        """Test receipts persist correctly in memory"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": "2022-01-01",
            "purchaseTime": "13:01",
            "items": [
                {
                    "shortDescription": "Mountain Dew",
                    "price": "6.49"
                }
            ],
            "total": "6.49"
        }
        
        # Add receipt
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        receipt_id = response.json()["id"]
        
        # Verify points
        points_response = client.get(f"/receipts/{receipt_id}/points")
        assert points_response.status_code == 200
        assert "points" in points_response.json() 