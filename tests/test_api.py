"""
Tests for API endpoints.
"""
import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_create_sku(client):
    """Test creating a SKU."""
    response = await client.post(
        "/api/v1/skus",
        json={
            "sku_code": "API-TEST-001",
            "name": "API Test Product",
            "description": "Test",
            "initial_qty": 50
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["sku_code"] == "API-TEST-001"
    assert data["name"] == "API Test Product"


@pytest.mark.asyncio
async def test_create_hold_endpoint(client, sample_sku):
    """Test create hold endpoint."""
    response = await client.post(
        "/api/v1/inventory/holds",
        json={
            "client_token": "api-test-token-1",
            "items": [
                {"sku_id": str(sample_sku.sku_id), "qty": 5}
            ],
            "expires_in_seconds": 300,
            "strategy": "optimistic"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "HELD"
    assert data["type"] == "HOLD"
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_get_availability_endpoint(client, sample_sku):
    """Test get availability endpoint."""
    response = await client.get(
        f"/api/v1/inventory/availability?sku_ids={sample_sku.sku_id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["sku_id"] == str(sample_sku.sku_id)
    assert data[0]["total_qty"] == 100


@pytest.mark.asyncio
async def test_consistency_check_endpoint(client):
    """Test consistency check endpoint."""
    response = await client.get("/api/v1/inventory/consistency")
    
    assert response.status_code == 200
    data = response.json()
    assert "is_consistent" in data
    assert "total_skus" in data

