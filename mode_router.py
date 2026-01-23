from modes.fixit import handle_fixit_mode
from modes.fridge_scanner import handle_fridge_scan
from modes.kitchen import handle_kitchen_mode, KitchenInput
from modes.home_organizer import handle_home_organizer_mode

from PIL import Image
import io


def get_mode(input_text: str) -> str:
    input_text_lower = input_text.lower()

    if "fix" in input_text_lower:
        return "Fixit"
    elif "fridge" in input_text_lower or "scan" in input_text_lower:
        return "Fridge"
    elif "kitchen" in input_text_lower or "cook" in input_text_lower:
        return "Kitchen"
    else:
        return "HomeOrganizer"


class ModeRouter:
    def detect_mode(self, input_text: str) -> str:
        return get_mode(input_text)

    def handle_mode(self, mode: str, input_text: str):
        if mode == "Fixit":
            return handle_fixit_mode(input_text)

        elif mode == "Fridge":
            from fastapi import UploadFile

            # ✅ Create a valid blank image in memory
            blank_image = Image.new("RGB", (100, 100), "white")
            image_bytes = io.BytesIO()
            blank_image.save(image_bytes, format="PNG")
            image_bytes.seek(0)

            # ✅ UploadFile does NOT take content_type
            dummy_file = UploadFile(
                filename="dummy.png",
                file=image_bytes
            )

            return handle_fridge_scan(dummy_file)

        elif mode == "Kitchen":
            kitchen_input = KitchenInput(
                fridge_items=["milk", "eggs"],
                pantry_items=["rice", "beans"],
                goal="make a healthy dinner",
                user_id="user_123"
            )
            return handle_kitchen_mode(kitchen_input)

        else:
            return handle_home_organizer_mode(input_text)
