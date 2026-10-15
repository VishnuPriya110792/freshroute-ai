from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_and_sample_data_endpoints():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    sample = client.get("/api/sample-data")
    assert sample.status_code == 200
    assert len(sample.json()["inventory"]) >= 5
    assert len(sample.json()["destinations"]) >= 2


def test_validation_and_compare_use_real_calculations():
    sample = client.get("/api/sample-data").json()
    validation = client.post("/api/inventory/validate", json={"inputs": sample})
    assert validation.status_code == 200
    assert validation.json()["valid"] is True
    comparison = client.post("/api/compare", json={"inputs": sample})
    assert comparison.status_code == 200
    body = comparison.json()
    assert body["optimized"]["metrics"]["total_available_kg"] > 0
    assert body["baseline"]["metrics"]["net_revenue_inr"] == body["baseline"]["metrics"]["gross_sales_inr"] - body["baseline"]["metrics"]["transport_cost_inr"]
    assert body["baseline"]["metrics"]["physically_expired_kg"] is None
    assert len(body["destination_summary"]) == len(sample["destinations"])
    assert sum(row["allocated_kg"] for row in body["destination_summary"]) == body["optimized"]["metrics"]["allocated_kg"]


def test_discount_and_scenario_endpoints_recalculate_a_separate_input_copy():
    sample = client.get("/api/sample-data").json()
    original_capacity = sample["destinations"][0]["capacity_kg"]
    discounts = client.post("/api/discounts", json={"inputs": sample})
    assert discounts.status_code == 200
    assert isinstance(discounts.json(), list)
    scenario = client.post("/api/scenarios/simulate", json={
        "inputs": sample, "travel_time_multiplier": 1, "demand_multiplier": 1, "capacity_multiplier": 0.5,
    })
    assert scenario.status_code == 200
    body = scenario.json()
    assert body["scenario_inputs"]["destinations"][0]["capacity_kg"] == original_capacity * 0.5
    assert sample["destinations"][0]["capacity_kg"] == original_capacity
    assert body["scenario"]["optimized"]["metrics"]["quantity_delivered_kg"] < body["original"]["optimized"]["metrics"]["quantity_delivered_kg"]


def test_invalid_csv_reports_useful_errors_without_silently_importing_rows():
    response = client.post(
        "/api/inventory/import",
        files={"file": ("inventory.csv", "batch_id,commodity\nB1,Tomatoes\n", "text/csv")},
    )
    assert response.status_code == 400
    body = response.json()["detail"]
    assert "missing required columns" in body["message"].lower()
    assert any("quantity_kg" in message for message in body["errors"])


def test_valid_csv_upload_is_parsed_as_real_inventory():
    csv_text = "batch_id,commodity,quantity_kg,shelf_life_hours,handling_notes,eligible_destinations\nB2,Tomatoes,12,36,Keep shaded,PUN;MUM\n"
    response = client.post("/api/inventory/import", files={"file": ("inventory.csv", csv_text, "text/csv")})
    assert response.status_code == 200
    assert response.json()["inventory"][0]["batch_id"] == "B2"
    assert response.json()["imported_rows"] == 1


def test_duplicate_csv_headers_are_rejected_explicitly():
    csv_text = "batch_id,batch_id,commodity,quantity_kg,shelf_life_hours,handling_notes,eligible_destinations\nB1,B2,Tomatoes,12,36,Keep shaded,PUN\n"
    response = client.post("/api/inventory/import", files={"file": ("inventory.csv", csv_text, "text/csv")})
    assert response.status_code == 400
    assert "duplicate column headers" in response.json()["detail"]["message"].lower()


def test_negative_quantity_returns_structured_422():
    sample = client.get("/api/sample-data").json()
    sample["inventory"][0]["quantity_kg"] = -3
    response = client.post("/api/compare", json={"inputs": sample})
    assert response.status_code == 422
    assert response.json()["error"] == "Validation failed"
    assert response.json()["details"]


def test_export_endpoints_return_generated_content():
    sample = client.get("/api/sample-data").json()
    allocations = client.post("/api/exports/allocations", json={"inputs": sample, "strategy": "optimized"})
    assert allocations.status_code == 200
    assert "batch_id" in allocations.text
    comparison = client.post("/api/exports/comparison", json={"inputs": sample})
    assert comparison.status_code == 200
    assert "net_revenue_inr" in comparison.text
    report = client.post("/api/reports/export", json={"inputs": sample, "scenario_label": "Test run"})
    assert report.status_code == 200
    assert "Test run" in report.text
    assert "Print / Save as PDF" in report.text
    assert "Pune Market" in report.text
    assert "Physical expiry is not observed" in report.text
    assert "Revenue trade-off" in report.text
