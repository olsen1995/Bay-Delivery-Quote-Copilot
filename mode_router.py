import sys
import re
from collections import defaultdict

class ModeRouter:
    def __init__(self):
        self.modes = {
            "DayPlanner": [
                "plan", "schedule", "calendar", "agenda", "itinerary", "organize", "mapped out"
            ],
            "LifeCoach": [
                "overwhelmed", "burnout", "unmotivated", "purpose", "stuck", "clarity",
                "self-sabotage", "focus", "mental", "motivation"
            ],
            "FixIt": [
                "broken", "fix", "repair", "leaking", "cracked", "wobbling", "not working",
                "malfunction", "jammed", "won’t start", "problem", "issue"
            ],
            "Device Optimization": [
                "slow", "optimize", "speed up", "performance", "battery", "startup apps",
                "cache", "lag", "storage", "overheating"
            ],
            "Kitchen": [
                "meal", "cook", "recipe", "food", "kitchen", "fridge", "grocery",
                "dinner", "breakfast", "lunch", "eggs", "rice", "ingredients", "leftovers"
            ],
            "Laundry": [
                "laundry", "clothes", "wash", "dryer", "stain", "detergent", "fabric",
                "bleach", "machine", "shrink", "sheets", "towels"
            ],
            "Cleaning": [
                "clean", "tidy", "declutter", "vacuum", "wipe", "disinfect", "dust",
                "mop", "sanitize", "smell", "odor", "reset"
            ],
            "Skincare": [
                "skincare", "acne", "retinol", "routine", "face", "pimple", "moisturizer",
                "barrier", "serum", "irritation", "dry skin", "oil", "cleanser"
            ],
            "RC Car": [
                "rc car", "remote control", "servo", "motor", "lipo", "ESC", "Hyper Go",
                "gearing", "brushless", "receiver", "speed controller", "battery pack"
            ],
            "Daily Horoscope": [
                "horoscope", "zodiac", "stars", "astrology", "aries", "leo", "cancer",
                "forecast", "daily horoscope", "gemini", "virgo"
            ],
            "Decision Check": [
                "should I", "decision", "decide", "choice", "option", "risk", "pros and cons",
                "buy", "sell", "move", "quit", "change"
            ]
        }

    def route(self, prompt):
        prompt = prompt.lower()
        mode_scores = defaultdict(int)

        for mode, keywords in self.modes.items():
            for keyword in keywords:
                if re.search(rf"\b{re.escape(keyword)}\b", prompt):
                    mode_scores[mode] += 1

        if not mode_scores:
            return "Unclassified", 0

        best_mode = max(mode_scores, key=mode_scores.get)
        return best_mode, mode_scores[best_mode]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mode_router.py \"your question here\"")
    else:
        router = ModeRouter()
        input_text = " ".join(sys.argv[1:])
        mode, score = router.route(input_text)
        print(f"🔍 Routed to Mode: {mode} (Confidence Score: {score})")
