from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

import backend.services.nhtsa_safety as nhtsa_safety
from backend.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_caches():
    nhtsa_safety._recalls_cache.clear()
    nhtsa_safety._complaints_cache.clear()
    yield
    nhtsa_safety._recalls_cache.clear()
    nhtsa_safety._complaints_cache.clear()


def _recall_record(**overrides):
    record = {
        "NHTSACampaignNumber": "19V005000",
        "Component": "AIR BAGS:FRONTAL:PASSENGER SIDE:INFLATOR MODULE",
        "Summary": "Recalling certain vehicles.",
        "Consequence": "An inflator explosion may result in injury.",
        "Remedy": "Dealers will replace the inflator.",
        "ReportReceivedDate": "09/01/2019",
    }
    record.update(overrides)
    return record


def _complaint_record(components: str):
    return {
        "odiNumber": 123,
        "components": components,
        "summary": "Something went wrong.",
    }


@pytest.mark.asyncio
async def test_get_open_recalls_returns_parsed_recalls():
    with patch.object(
        nhtsa_safety, "_get", AsyncMock(return_value={"results": [_recall_record()]})
    ):
        result = await nhtsa_safety.get_open_recalls("Toyota", "Corolla", "2010")

    assert result.count == 1
    assert result.open_recalls[0].campaign_number == "19V005000"
    assert "inflator" in result.open_recalls[0].consequence.lower()


@pytest.mark.asyncio
async def test_get_open_recalls_empty_when_no_recalls():
    with patch.object(nhtsa_safety, "_get", AsyncMock(return_value={"results": []})):
        result = await nhtsa_safety.get_open_recalls("Toyota", "Corolla", "2010")

    assert result.count == 0
    assert result.open_recalls == []


@pytest.mark.asyncio
async def test_get_open_recalls_degrades_gracefully_on_nhtsa_failure():
    with patch.object(
        nhtsa_safety, "_get", AsyncMock(side_effect=httpx.ConnectError("boom"))
    ):
        result = await nhtsa_safety.get_open_recalls("Toyota", "Corolla", "2010")

    assert result.count == 0
    assert result.open_recalls == []


@pytest.mark.asyncio
async def test_get_open_recalls_caches_repeat_lookups():
    mock_get = AsyncMock(return_value={"results": [_recall_record()]})
    with patch.object(nhtsa_safety, "_get", mock_get):
        await nhtsa_safety.get_open_recalls("Toyota", "Corolla", "2010")
        await nhtsa_safety.get_open_recalls("toyota", "corolla", "2010")  # case-insensitive same key

    assert mock_get.call_count == 1


@pytest.mark.asyncio
async def test_get_complaints_summary_aggregates_multi_component_complaints():
    records = {
        "results": [
            _complaint_record("POWER TRAIN,AIR BAGS,ENGINE"),
            _complaint_record("ENGINE"),
            _complaint_record("ELECTRICAL SYSTEM"),
        ]
    }
    with patch.object(nhtsa_safety, "_get", AsyncMock(return_value=records)):
        result = await nhtsa_safety.get_complaints_summary("Toyota", "Corolla", "2010")

    assert result.total_complaints == 3
    top = {c.component: c.count for c in result.top_components}
    assert top["ENGINE"] == 2
    assert top["POWER TRAIN"] == 1
    assert top["AIR BAGS"] == 1
    assert top["ELECTRICAL SYSTEM"] == 1


@pytest.mark.asyncio
async def test_get_complaints_summary_degrades_gracefully_on_nhtsa_failure():
    with patch.object(
        nhtsa_safety, "_get", AsyncMock(side_effect=httpx.TimeoutException("boom"))
    ):
        result = await nhtsa_safety.get_complaints_summary("Toyota", "Corolla", "2010")

    assert result.total_complaints == 0
    assert result.top_components == []


def test_recalls_endpoint_requires_year_make_model(client):
    response = client.get("/api/vehicle-safety/recalls?year=&make=Toyota&model=Corolla")
    assert response.status_code == 422


def test_recalls_endpoint_returns_data(client):
    with patch.object(
        nhtsa_safety, "_get", AsyncMock(return_value={"results": [_recall_record()]})
    ):
        response = client.get(
            "/api/vehicle-safety/recalls?year=2010&make=Toyota&model=Corolla"
        )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_complaints_summary_endpoint_returns_data(client):
    with patch.object(
        nhtsa_safety,
        "_get",
        AsyncMock(return_value={"results": [_complaint_record("ENGINE")]}),
    ):
        response = client.get(
            "/api/vehicle-safety/complaints-summary?year=2010&make=Toyota&model=Corolla"
        )
    assert response.status_code == 200
    assert response.json()["total_complaints"] == 1
