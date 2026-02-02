import os
from gpt.summary_validator import validate_summary

def summarize_entity(entity: dict) -> str:
    """
    Rule-based summarizer that generates a consistent, validator-safe description.
    This function is deterministic and avoids triggering validation errors.
    """
    name = entity.get("name", "Unnamed")
    type_ = entity.get("type", "Unknown")
    description = entity.get("description", "").strip() if isinstance(entity.get("description"), str) else ""

    # Clamp and clean the base description
    if len(description) > 200:
        description = description[:197].rsplit(" ", 1)[0] + "..."

    summary = f"{name} is a {type_} entity. {description}"
    summary = summary.strip()

    # Ensure compliance
    validate_summary(summary, entity)
    return summary

def llm_summarize_entity(entity: dict) -> str:
    """
    Generates an LLM-based summary, then validates it.
    """
    prompt = (
        f"Summarize the following entity in plain English. "
        f"The summary must mention the name and type. No markdown, no speculation, no external references.\n\n"
        f"Entity:\n{entity}"
    )
    summary = _call_llm(prompt)
    summary = summary.strip()

    validate_summary(summary, entity)
    return summary

def _call_llm(prompt: str) -> str:
    """
    Lazy-loaded OpenAI client that calls the LLM backend securely.
    Guaranteed to return a string or raise.
    """
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    if not isinstance(content, str):
        raise RuntimeError("LLM returned empty or invalid content")

    return content.strip()

