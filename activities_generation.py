"""
Travel Planner — Claude API Client

Thin wrapper around the Anthropic API with web search enabled.
You supply the system prompt and user message, this handles the rest.

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY="your-key-here"

Usage:
    from generate_activities import request_activities

    system_prompt = "Your prompt here..."
    user_message = "Generate 30 activities for New York City"

    result = request_activities(system_prompt, user_message)
    # result is a parsed dict if Claude returned valid JSON,
    # or raw string if parsing failed.
"""

import anthropic
import json


def load_prompt(description, json_schema) -> str:
    with open(description, "r") as f:
        descr = f.read()

    with open(json_schema, "r") as f:
        schema = f.read()

        return descr + "\n" + schema + "Return ONLY a valid JSON array of activity objects. No markdown fences, no commentary."

        


def request_activities(
    user_message: str,
    system_prompt: str = None,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 16000,
    max_searches: int = 20,
    temperature: float = 0.0,
) -> dict | str:
    """
    Send a prompt to Claude with web search enabled and return the response.

    Args:
        user_message:  The user-turn message (e.g. "Generate 30 activities for Tokyo").
        system_prompt: The system prompt
        model:         Anthropic model string.
        max_tokens:    Max output tokens. 16k is generous for ~30 activities.
        max_searches:  How many web searches Claude is allowed per request.
        temperature:   0.0 for deterministic, increase for variety.

    Returns:
        Parsed dict if the response is valid JSON, otherwise the raw text string.
    """
    if system_prompt is None:
        system_prompt = load_prompt("prompt.txt", "schema.txt")

    client = anthropic.Anthropic()

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": max_searches,
        }],
    ) as stream:
        response = stream.get_final_message()

    return _extract_json(response)



def _extract_json(response) -> dict | str:
    """
    Pull text blocks from the response, find the JSON, and parse it.
    Falls back to returning the raw text if parsing fails.
    """
    text_parts = [
        block.text
        for block in response.content
        if block.type == "text"
    ]
    raw = "\n".join(text_parts).strip()

    # Strip markdown fences if the model wrapped its output
    cleaned = raw
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return raw


def save(data, path: str = "out.json") -> None:
    with open(path, "w") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, indent=2)
