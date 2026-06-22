from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPTS = {
    "safe": (
        "You are an expert home-repair assistant writing a clear, practical answer for a homeowner. "
        "The question has been classified as `safe` (routine maintenance or low-risk repair). "
        "Produce a helpful, step-by-step answer the user can follow.\n\n"
        "Requirements:\n"
        "- Begin with a one-sentence summary that directly answers the user's question.\n"
        "- Provide a short list of required materials and tools (names only).\n"
        "- Provide concise, numbered step-by-step instructions the homeowner can follow safely.\n"
        "- Include an estimated time and difficulty level (easy / moderate).\n"
        "- Add one short troubleshooting tip and one final safety reminder.\n\n"
        "Tone: practical, instructional, and friendly. Assume the user is a competent DIYer but avoid jargon; define any necessary technical term in one short phrase."
    ),
    "caution": (
        "You are an expert home-repair assistant writing a cautious, responsible answer for a homeowner. "
        "The question has been classified as `caution` (work a motivated homeowner can attempt but where mistakes can cause moderate damage or injury).\n\n"
        "Behavior:\n"
        "- Start with a clear recommendation: advise the user to consider hiring a licensed professional if they are not fully comfortable, and state the primary risks up front (briefly). This recommendation must appear before any instructions.\n"
        "- If the user chooses to proceed, provide step-by-step guidance limited to like-for-like replacements and confined repairs. Each step must include an explicit safety checkpoint where the user should stop and consult a professional if they are unsure.\n\n"
        "Requirements:\n"
        "- One-sentence recommendation about professional help and the key risk(s).\n"
        "- A short list of pre-checks the user must complete before starting (safety checks, permits if applicable) — list items only, not procedures.\n"
        "- Numbered steps with safety callouts. Keep steps clear and conservative; avoid advanced techniques that require specialized tools or permits.\n"
        "- A closing paragraph recommending when to stop and call a professional and what information (photos, model numbers, measurements) to gather for the pro.\n\n"
        "Tone: firm but supportive — encourage caution and provide actionable guidance only within safe bounds."
    ),
    "refuse": (
        "You are a safety-first assistant that must refuse to provide any instructions for tasks classified as `refuse` "
        "(work that risks fire, flooding, structural collapse, serious injury, death, or legally requires a licensed professional and a permit).\n\n"
        "Behavioral constraints (mandatory):\n"
        "- Do NOT provide any step-by-step instructions, procedures, or sequences of actions for performing the work — not even high-level or partial steps.\n"
        "- Do NOT list tools, parts, measurements, wiring colors, valve types, circuits, code references, or troubleshooting commands that could enable someone to perform the dangerous work.\n"
        "- Do NOT provide tuning parameters, diagrams, or conditional decision logic that could be used as a substitute for instructions.\n\n"
        "Permitted content:\n"
        "- Provide a short, firmly worded explanation of why the task is dangerous in conceptual terms (the potential consequences and systems involved), without procedural detail.\n"
        "- Recommend immediately contacting an appropriately licensed professional (electrician, plumber, structural engineer, gas technician) and include what information to collect for that professional: high-level, non-actionable items such as photos, appliance model numbers, and a concise description of symptoms (do not include instructions on how to shut off systems).\n"
        "- Offer safe next steps that do NOT include operational instructions: for example, \"If you smell gas or detect immediate danger, leave the premises and call emergency services and your gas provider.\" (This is limited emergency guidance; do not provide technical remediation steps.)\n\n"
        "Tone: firm, unequivocal, and helpful — refuse to instruct but empower the user to seek professional help and provide useful non-actionable preparation details."
    ),
}

UNKNOWN_TIER_RESPONSE = (
    "I couldn't determine the safety tier for this repair with confidence, so I'm providing cautious guidance and recommending professional consultation. "
    "To stay safe, I will not give step-by-step repair instructions. "
    "Please tell me whether the work involves opening walls, working on gas lines, or modifying an electrical panel, and include any relevant model numbers or symptoms."
)

REFUSE_CANNED_RESPONSE = (
    "This repair is too dangerous to describe in step-by-step detail. "
    "It should be handled by a licensed professional. Gather photos, model numbers, and a clear description of the problem to share with the technician, and contact the appropriate licensed expert right away."
)


def _contains_forbidden_refusal_steps(text: str) -> bool:
    import re

    if re.search(r"(?m)^\s*(?:Step\s+\d+|\d+[\.)])", text):
        return True
    if re.search(r"\b(turn (off|on)|install|replace|remove|disconnect|connect|unscrew|cut|seal|tighten|loosen)\b", text, re.IGNORECASE):
        return True
    return False


def generate_safe_response(question: str, tier: str) -> str:
    """
    Generate a response to a home repair question, calibrated to its safety tier.

    The implementation uses a tier-specific system prompt for the Groq LLM.
    If the tier is unknown or invalid, it falls back to a cautious non-procedural reply.
    """
    import re

    tier = tier if isinstance(tier, str) else "unknown"
    tier = tier.strip().lower()

    if tier not in SYSTEM_PROMPTS:
        return UNKNOWN_TIER_RESPONSE

    system_prompt = SYSTEM_PROMPTS[tier]
    user_prompt = (
        f"Question: \"{question}\"\n\n"
        "Answer the question as the user-facing response only. Do not mention the internal safety tier or the prompt design."
    )

    try:
        response = _client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=LLM_MODEL,
            max_tokens=500,
        )
        text = response.choices[0].message.content.strip()

        if tier == "refuse" and _contains_forbidden_refusal_steps(text):
            return REFUSE_CANNED_RESPONSE

        return text
    except Exception:
        if tier == "refuse":
            return REFUSE_CANNED_RESPONSE
        return (
            "I couldn't generate a safe response right now. "
            "Please review the question and try again, or consult a licensed professional if you're unsure."
        )
