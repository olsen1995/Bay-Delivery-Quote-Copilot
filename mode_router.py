
import sys
import re
from collections import defaultdict

class ModeRouter:
    def __init__(self):
        self.modes = {
            "DayPlanner": ["schedule", "plan", "calendar", "appointment", "meeting", "itinerary"],
            "LifeCoach": ["motivation", "goals", "purpose", "burnout", "discipline", "growth"],
            "FixIt": ["broken", "repair", "fix", "malfunction", "not working", "diagnose"],
            "Device Optimization": ["battery", "slow", "performance", "optimize", "speed up"],
            "Kitchen": ["meal", "cook", "recipe", "food", "kitchen", "fridge", "grocery"],
            "Laundry": ["laundry", "clothes", "washer", "dryer", "fabric", "detergent"],
            "Cleaning": ["clean", "mess", "tidy", "declutter", "vacuum", "dust"],
            "Skincare": ["acne", "skincare", "routine", "face", "dry skin", "moisturizer"],
            "RC Car": ["rc car", "remote control", "servo", "motor", "lipo battery"],
            "Daily Horoscope": ["horoscope", "zodiac", "astrology", "leo", "capricorn", "stars"],
            "Decision Check": ["decide", "decision", "choose", "option", "should I", "pros and cons"]
        }

    def route(self, prompt):
        prompt = prompt.lower()
        mode_scores = defaultdict(int)

        for mode, keywords in self.modes.items():
            for keyword in keywords:
                # Boost score if keyword is present
                if re.search(rf"\b{re.escape(keyword)}\b", prompt):
                    mode_scores[mode] += 1

        if not mode_scores:
            return "Unclassified", 0

        # Get the mode with the highest score
        best_mode = max(mode_scores, key=mode_scores.get)
        return best_mode, mode_scores[best_mode]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mode_router.py 'your question here'")
    else:
        router = ModeRouter()
        input_text = " ".join(sys.argv[1:])
        mode, score = router.route(input_text)
        print(f"🔍 Routed to Mode: {mode} (Confidence Score: {score})")

