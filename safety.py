from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into one of three safety tiers.

    TODO — Milestone 1:

    Before writing any code, complete specs/classifier-spec.md. The blank fields
    there are the decisions that drive this implementation — prompt design, tier
    definitions, output format, and edge case handling.

    Your implementation should:
      1. Build a prompt using your tier definitions that asks the LLM to classify
         the question and explain its reasoning
      2. Send a single chat completion request (no tools, no history)
      3. Parse the tier and reason out of the raw response text
      4. Validate the tier against VALID_TIERS; fall back to "caution" if the
         response can't be parsed or the tier isn't recognized
      5. Return {"tier": ..., "reason": ...}

    Returns a dict with:
      - "tier"   : str — one of "safe", "caution", "refuse"
      - "reason" : str — a brief explanation of why this tier was assigned

    The three tiers:
      - "safe"    : routine, low-risk repairs most homeowners can handle safely
      - "caution" : doable with care, but mistakes have real cost or mild risk
      - "refuse"  : high-risk repairs that require a licensed professional —
                    mistakes can cause fire, flooding, injury, or structural damage
    """
    import json
    import re

    system_message = (
      "You are a safety-tier classifier for homeowner repair questions. "
      "Use the following precise tier definitions and edge-case rules to decide whether a question is `safe`, `caution`, or `refuse`.\n\n"
      "Tier definitions:\n"
      "- safe: Routine maintenance and low-risk repairs that most homeowners can complete with basic hand tools and no permit; worst-case outcomes are cosmetic or minor inconvenience.\n"
      "- caution: Repairs a motivated homeowner can perform but where mistakes can cause moderate damage or personal injury or involve building systems (water, electrical). Typically like-for-like replacements or repairs confined to existing fixtures, wiring, or piping.\n"
      "- refuse: Repairs that risk fire, flooding, structural collapse, serious injury, or death — or work that legally requires a licensed professional and a permit (examples: electrical panel work, adding new circuits or outlets, gas-line work, major plumbing, removing load-bearing walls, replacing a water heater).\n\n"
      "Edge-case rules:\n"
      "- Gas-related questions: always refuse.\n"
      "- 'Replace' vs 'Add new' for electrical: replacing an existing device at the same location is caution; adding new outlets/circuits is refuse.\n"
      "- Wall removal: unless the user confirms a structural engineer or permit says non-load-bearing, classify as refuse.\n"
      "- Water heater replacement: classify as refuse unless explicitly limited to a minor component.\n\n"
      "Do NOT output chain-of-thought. Output only the final classification in the exact JSON format requested by the user."
    )

    user_message = (
      "Classify the following homeowner question. Output exactly one JSON object and nothing else, using keys `tier` and `reason`.\n\n"
      "Question: \"{question}\"\n\n"
      "Few-shot examples (for guidance):\n"
      "1) \"How do I patch a small hole in drywall?\"\n"
      "=> {\"tier\": \"safe\", \"reason\": \"Patching a small drywall hole is routine maintenance with no permit and low risk of injury or major damage.\"}\n\n"
      "2) \"How do I replace an outlet that stopped working?\"\n"
      "=> {\"tier\": \"caution\", \"reason\": \"Replacing an existing outlet at the same location is a like-for-like swap and carries limited risk if power is isolated.\"}\n\n"
      "3) \"How do I add a new outlet in my garage?\"\n"
      "=> {\"tier\": \"refuse\", \"reason\": \"Adding a new outlet requires new wiring and possibly opening the electrical panel, which risks fire and typically requires a permit and a licensed electrician.\"}\n"
    ).replace("{question}", question)

    try:
      resp = _client.chat.completions.create(
        messages=[
          {"role": "system", "content": system_message},
          {"role": "user", "content": user_message},
        ],
        model=LLM_MODEL,
        max_tokens=300,
      )

      raw = resp.choices[0].message.content

      # Extract JSON object from the model output robustly
      m = re.search(r"\{.*\}", raw, re.DOTALL)
      if not m:
        raise ValueError("no json object found in model output")

      json_text = m.group(0)
      parsed = json.loads(json_text)

      tier = parsed.get("tier")
      reason = parsed.get("reason")

      if not isinstance(tier, str) or not isinstance(reason, str):
        raise ValueError("missing keys or wrong types in parsed JSON")

      tier = tier.strip().lower()
      reason = reason.strip()

      if tier not in VALID_TIERS:
        raise ValueError(f"invalid tier: {tier}")

      return {"tier": tier, "reason": reason}

    except Exception:
      # Fail closed: return caution and a short clarifying reason
      return {
        "tier": "caution",
        "reason": (
          "Classification unclear or unparsable; defaulting to caution. "
          "Please provide more details or confirm the scope of work."
        ),
      }
