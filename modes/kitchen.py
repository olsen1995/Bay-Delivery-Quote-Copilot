from pydantic import BaseModel
from typing import List, Dict

class KitchenInput(BaseModel):
    fridge_items: List[str]
    pantry_items: List[str]
    dietary_preferences: List[str] = []
    goal: str  # e.g. "dinner recipe", "grocery list", "meal prep ideas"

class KitchenResponse(BaseModel):
    goal: str
    suggestions: List[str]

# Simulated recipe and suggestion engine
def handle_kitchen_mode(data: KitchenInput) -> KitchenResponse:
    suggestions = []

    # Sample logic: recipe suggestion
    if "dinner" in data.goal.lower():
        if "chicken" in data.fridge_items and "rice" in data.pantry_items:
            suggestions.append("How about chicken stir-fry with rice?")
        elif "eggs" in data.fridge_items and "bread" in data.pantry_items:
            suggestions.append("You can make a savory French toast with eggs and bread.")
        else:
            suggestions.append("You might need to pick up a few fresh ingredients for dinner.")

    # Grocery recommendation
    if "grocery" in data.goal.lower():
        needed_items = ["milk", "eggs", "bread", "spinach"]
        missing = [item for item in needed_items if item not in data.fridge_items + data.pantry_items]
        if missing:
            suggestions.append(f"You are low on: {', '.join(missing)}")
        else:
            suggestions.append("You're fully stocked for the basics!")

    # Meal prep
    if "meal prep" in data.goal.lower():
        suggestions.append("Consider prepping overnight oats with almond milk and chia seeds.")
        suggestions.append("Cook a large batch of rice and grilled veggies for the week.")

    if not suggestions:
        suggestions.append("No suggestions available for the given input.")

    return KitchenResponse(goal=data.goal, suggestions=suggestions)
