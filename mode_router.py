from modes.dayplanner import handle_dayplanner_mode
from modes.lifecoach import handle_lifecoach_mode
from modes.fixit import handle_fixit_mode
from modes.home_organizer import handle_home_organizer_mode

class ModeRouter:
    def detect_mode(self, input_text: str) -> str:
        lowered = input_text.lower()
        if "schedule" in lowered or "plan my day" in lowered:
            return "DayPlanner"
        elif "fix" in lowered or "debug" in lowered:
            return "FixIt"
        elif "organize" in lowered or "declutter" in lowered or "clean" in lowered:
            return "HomeOrganizer"
        else:
            return "LifeCoach"

    def handle_mode(self, mode: str, input_text: str):
        if mode == "DayPlanner":
            return handle_dayplanner_mode(input_text)
        elif mode == "FixIt":
            return handle_fixit_mode(input_text)
        elif mode == "HomeOrganizer":
            return handle_home_organizer_mode(input_text)
        else:
            return handle_lifecoach_mode(input_text)
