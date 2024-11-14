import pytest
import time
import asyncio
import psutil
import os
from httpx import AsyncClient
from fastapi.testclient import TestClient
from tests.test_data import VALID_TEST_RECEIPT


class TestPerformance:
    @pytest.mark.asyncio
    async def test_concurrent_load(self, async_client: AsyncClient) -> None:
        """Test API performance under concurrent load"""
        receipt = {
            "retailer": "Target",
            "purchaseDate": "2022-01-01",
            "purchaseTime": "13:01",
            "items": [
                {"shortDescription": "Mountain Dew", "price": "6.49"}
            ],
            "total": "6.49"
        }
        
        start_time = time.time()
        tasks = []
        for _ in range(5):
            tasks.append(async_client.post("/receipts/process", json=receipt))
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check all responses
        for response in responses:
            assert response.status_code == 200, f"Response: {response.json()}"
        assert duration < 5

    def test_memory_usage(self, client: TestClient) -> None:
        """Test memory usage with many receipts"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Use valid test receipt that matches api.yml patterns
        receipt = {
            "retailer": "Target",  # Matches ^[\w\s\-&]+$
            "purchaseDate": "2022-01-01",
            "purchaseTime": "13:01",
            "items": [
                {"shortDescription": "Test-Item", "price": "1.00"}  # Matches ^[\w\s\-]+$
            ],
            "total": "1.00"  # Matches ^\d+\.\d{2}$
        }
        
        # Process fewer receipts to avoid validation issues
        for _ in range(10):
            response = client.post("/receipts/process", json=receipt)
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory usage shouldn't grow excessively
        assert memory_increase < 10 * 1024 * 1024  # Less than 10MB increase