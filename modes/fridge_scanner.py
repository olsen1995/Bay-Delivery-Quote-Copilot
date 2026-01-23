from typing import List
from fastapi import UploadFile
import random

class FridgeScanResult:
    def __init__(self, ingredients: List[str], recipes: List[str]):
        self.ingredients = ingredients
        self.recipes = recipes

# Simulated image-to-ingredient model
def fake_image_recognizer(file: UploadFile) -> List[str]:
    mock_ingredients = [
        "milk", "eggs", "cheese", "lettuce", "tomato", "chicken",
        "carrot", "yogurt", "onion", "spinach", "butter", "rice"
    ]
    return random.sample(mock_ingredients, k=5)

def handle_fridge_scan(file: UploadFile) -> FridgeScanResult:
    detected = fake_image_recognizer(file)

    # Basic rule-based recipes
    recipes = []
    if "eggs" in detected and "milk" in detected:
        recipes.append("Omelette")
    if "chicken" in detected and "rice" in detected:
        recipes.append("Chicken Rice Bowl")
    if "lettuce" in detected and "tomato" in detected:
        recipes.append("Simple Salad")

    if not recipes:
        recipes.append("Not enough ingredients detected for a known recipe.")

    return FridgeScanResult(ingredients=detected, recipes=recipes)
