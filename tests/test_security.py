from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient
from tests.test_data import VALID_TEST_RECEIPT

class TestSecurity:
    def test_receipt_id_format(self, client: TestClient) -> None:
        """Test receipt ID format for predictability/security"""
        receipt = VALID_TEST_RECEIPT
        response = client.post("/receipts/process", json=receipt)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert " " not in data["id"]  # Matches pattern ^\S+$

    def test_path_traversal(self, client: TestClient) -> None:
        """Test protection against path traversal"""
        path = "../../../etc/passwd"
        response = client.get(f"/receipts/{path}/points")
        assert response.status_code == 404
        assert "detail" in response.json()