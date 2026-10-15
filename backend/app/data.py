from __future__ import annotations

from .models import PlanInput


# Illustrative synthetic inputs only: not official statistics or current market quotes.
SAMPLE_DATA: dict = {
    "inventory": [
        {"batch_id": "TOM-041", "commodity": "Tomatoes", "quantity_kg": 420, "shelf_life_hours": 30, "handling_notes": "Keep shaded; avoid compression", "eligible_destinations": ["PUN", "MUM", "NAS"]},
        {"batch_id": "TOM-042", "commodity": "Tomatoes", "quantity_kg": 300, "shelf_life_hours": 54, "handling_notes": "Ventilated crates", "eligible_destinations": ["PUN", "MUM", "NAS"]},
        {"batch_id": "BAN-018", "commodity": "Bananas", "quantity_kg": 360, "shelf_life_hours": 48, "handling_notes": "Do not stack above 5 crates", "eligible_destinations": ["PUN", "MUM"]},
        {"batch_id": "MAN-009", "commodity": "Mangoes", "quantity_kg": 240, "shelf_life_hours": 72, "handling_notes": "Handle gently; ventilated crates", "eligible_destinations": ["MUM", "NAS"]},
        {"batch_id": "ONI-031", "commodity": "Onions", "quantity_kg": 500, "shelf_life_hours": 240, "handling_notes": "Keep dry", "eligible_destinations": ["PUN", "MUM", "NAS"]},
        {"batch_id": "GRE-006", "commodity": "Leafy greens", "quantity_kg": 180, "shelf_life_hours": 18, "handling_notes": "Keep cool; dispatch immediately", "eligible_destinations": ["PUN", "NAS"]},
        {"batch_id": "GRE-007", "commodity": "Leafy greens", "quantity_kg": 140, "shelf_life_hours": 32, "handling_notes": "Keep cool", "eligible_destinations": ["PUN", "NAS"]},
    ],
    "destinations": [
        {
            "destination_id": "PUN", "name": "Pune Market", "travel_hours": 5, "handling_hours": 2,
            "transport_cost_inr_per_kg": 3.2, "capacity_kg": 820,
            "demand_by_commodity": {"Tomatoes": 500, "Bananas": 260, "Onions": 330, "Leafy greens": 140},
            "price_by_commodity": {"Tomatoes": 27, "Bananas": 34, "Onions": 22, "Leafy greens": 48},
        },
        {
            "destination_id": "MUM", "name": "Mumbai Market", "travel_hours": 9, "handling_hours": 3,
            "transport_cost_inr_per_kg": 5.4, "capacity_kg": 900,
            "demand_by_commodity": {"Tomatoes": 430, "Bananas": 300, "Mangoes": 220, "Onions": 300},
            "price_by_commodity": {"Tomatoes": 31, "Bananas": 38, "Mangoes": 86, "Onions": 25},
        },
        {
            "destination_id": "NAS", "name": "Nashik Market", "travel_hours": 4, "handling_hours": 2,
            "transport_cost_inr_per_kg": 2.6, "capacity_kg": 540,
            "demand_by_commodity": {"Tomatoes": 220, "Mangoes": 180, "Onions": 240, "Leafy greens": 100},
            "price_by_commodity": {"Tomatoes": 24, "Mangoes": 78, "Onions": 20, "Leafy greens": 44},
        },
    ],
}


def sample_input() -> PlanInput:
    return PlanInput.model_validate(SAMPLE_DATA)
