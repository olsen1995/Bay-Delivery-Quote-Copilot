from typing import List, Dict, Any

def gpt_reason(intent: str, context: str, canon_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    # 
    references = []
    reasoning = f"Intent received: '{intent}'. Evaluating relevant canon entries."

    for ctype, entries in canon_data.items():
        for entry in entries:
            if intent.lower() in entry.get("description", "").lower():
                references.append({"type": ctype, "name": entry["name"]})

    return {
        "status": "ok",
        "reasoning": reasoning,
        "references": references,
        "confidence": 0.91  # Static placeholder
    }
