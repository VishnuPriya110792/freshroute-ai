from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .data import sample_input
from .discounts import recommend_discounts
from .evaluation import compare_plans
from .models import AllocationExportRequest, InputRequest, PlanInput, ReportRequest, ScenarioRequest
from .planner import fefo_baseline, optimize
from .reports import allocations_csv, comparison_csv, summary_html
from .scenarios import simulate

app = FastAPI(
    title="FreshRoute AI API",
    description=(
        "Deterministic decision support for synthetic perishable-produce distribution. "
        "All quantities are kg, time is hours, and prices/costs are INR per kg unless specified."
    ),
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.exception_handler(RequestValidationError)
async def request_validation_error(_, exc: RequestValidationError):
    details = []
    for error in exc.errors():
        details.append({
            "location": ".".join(str(part) for part in error.get("loc", [])),
            "message": error.get("msg", "Invalid input"),
            "type": error.get("type", "validation_error"),
        })
    return JSONResponse(status_code=422, content={"error": "Validation failed", "details": details})


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "freshroute-api"}


@app.get("/api/sample-data", response_model=PlanInput)
def get_sample_data() -> PlanInput:
    return sample_input()


@app.post("/api/inventory/validate")
def validate_inventory(request: InputRequest) -> dict:
    inputs = request.inputs
    return {
        "valid": True,
        "inventory_batches": len(inputs.inventory),
        "destinations": len(inputs.destinations),
        "total_inventory_kg": sum(row.quantity_kg for row in inputs.inventory),
        "messages": ["All inputs passed structural and hard-constraint validation."],
        "disclosure": "Validation checks input structure, not the physical accuracy of estimates.",
    }


@app.post("/api/inventory/import")
async def import_inventory(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    if len(raw) > 2_000_000:
        raise HTTPException(status_code=413, detail={"message": "CSV exceeds the 2 MB upload limit."})
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail={"message": "CSV must use UTF-8 text encoding."})
    reader = csv.DictReader(io.StringIO(text))
    required = {"batch_id", "commodity", "quantity_kg", "shelf_life_hours", "handling_notes", "eligible_destinations"}
    fieldnames = reader.fieldnames or []
    if len(fieldnames) != len(set(fieldnames)):
        raise HTTPException(status_code=400, detail={"message": "CSV contains duplicate column headers.", "errors": ["Each required column must appear exactly once."]})
    headers = set(fieldnames)
    missing = sorted(required - headers)
    if missing:
        raise HTTPException(status_code=400, detail={"message": "CSV is missing required columns.", "errors": [f"Missing column: {column}" for column in missing]})
    inventory = []
    errors: list[str] = []
    for line_number, row in enumerate(reader, start=2):
        if None in row:
            errors.append(f"Row {line_number}: too many fields; check the CSV column count.")
            continue
        try:
            parsed = {
                "batch_id": row.get("batch_id", ""),
                "commodity": row.get("commodity", ""),
                "quantity_kg": float(row.get("quantity_kg", "")),
                "shelf_life_hours": float(row.get("shelf_life_hours", "")),
                "handling_notes": row.get("handling_notes") or "",
                "eligible_destinations": [part.strip() for part in (row.get("eligible_destinations") or "").split(";") if part.strip()],
            }
            from .models import InventoryBatch
            inventory.append(InventoryBatch.model_validate(parsed))
        except (TypeError, ValueError, ValidationError) as exc:
            errors.append(f"Row {line_number}: {exc}")
    identifiers = [item.batch_id for item in inventory]
    if len(identifiers) != len(set(identifiers)):
        errors.append("Duplicate batch_id values were found; identifiers must be unique.")
    if errors:
        raise HTTPException(status_code=400, detail={
            "message": f"CSV contains {len(errors)} validation error(s); no rows were imported.",
            "errors": errors,
            "valid_rows_before_errors": len(inventory),
        })
    if not inventory:
        raise HTTPException(status_code=400, detail={"message": "CSV contains a header but no inventory rows."})
    return {"valid": True, "inventory": [row.model_dump() for row in inventory], "imported_rows": len(inventory)}


@app.get("/api/templates/inventory.csv")
def inventory_template() -> Response:
    content = "batch_id,commodity,quantity_kg,shelf_life_hours,handling_notes,eligible_destinations\nTOM-EXAMPLE,Tomatoes,100,36,Keep shaded,PUN;MUM\n"
    return Response(content=content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=freshroute-inventory-template.csv"})


@app.post("/api/optimize")
def optimize_route(request: InputRequest):
    return optimize(request.inputs)


@app.post("/api/compare")
def compare_route(request: InputRequest):
    return compare_plans(request.inputs, fefo_baseline(request.inputs), optimize(request.inputs))


@app.post("/api/discounts")
def discounts_route(request: InputRequest):
    plan = optimize(request.inputs)
    return recommend_discounts(request.inputs, plan)


@app.post("/api/scenarios/simulate")
def simulate_route(request: ScenarioRequest):
    return simulate(request)


@app.post("/api/exports/allocations")
def export_allocations(request: AllocationExportRequest) -> Response:
    comparison = compare_plans(request.inputs, fefo_baseline(request.inputs), optimize(request.inputs))
    plan = comparison.optimized if request.strategy == "optimized" else comparison.baseline
    return Response(
        content=allocations_csv(plan),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=freshroute-{request.strategy}-allocations.csv"},
    )


@app.post("/api/exports/comparison")
def export_comparison(request: InputRequest) -> Response:
    comparison = compare_plans(request.inputs, fefo_baseline(request.inputs), optimize(request.inputs))
    return Response(
        content=comparison_csv(comparison),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=freshroute-baseline-comparison.csv"},
    )


@app.post("/api/reports/export", response_class=HTMLResponse)
def export_report(request: ReportRequest) -> HTMLResponse:
    comparison = compare_plans(request.inputs, fefo_baseline(request.inputs), optimize(request.inputs))
    discounts = recommend_discounts(request.inputs, comparison.optimized)
    report = summary_html(request.inputs, comparison, discounts, request.scenario_label)
    return HTMLResponse(
        content=report,
        headers={"Content-Disposition": "attachment; filename=freshroute-distribution-summary.html"},
    )


@app.get("/{path:path}")
def serve_dashboard(path: str):
    if path.startswith("api/") or path in {"health", "docs", "redoc", "openapi.json"}:
        raise HTTPException(status_code=404, detail="Not found")
    if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file():
        requested = FRONTEND_DIST / path
        if path and requested.is_file() and FRONTEND_DIST in requested.resolve().parents:
            return FileResponse(requested)
        return Response(content=(FRONTEND_DIST / "index.html").read_bytes(), media_type="text/html")
    return HTMLResponse(
        "<h1>FreshRoute AI is starting</h1><p>Build the React app with <code>npm run build --prefix frontend</code>, then restart the API.</p>",
        status_code=503,
    )
