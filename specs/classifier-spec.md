# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Tier definitions

*Write a one-sentence definition for each tier that is precise enough to use as part of your classification prompt. Vague definitions produce inconsistent classifications.*

**safe:**
```
Routine maintenance and low-risk repairs that most homeowners can complete with basic hand tools and no permit or licensed professional; if done incorrectly the worst-case outcomes are cosmetic damage or minor inconvenience (not fire, flooding, structural failure, or serious injury).
```

**caution:**
```
Repairs a motivated homeowner can attempt but where mistakes can cause moderate damage or personal injury or involve building systems (water, electrical) — typically no permit is required, but the work should be limited to like-for-like replacements or repairs confined to existing fixtures, wiring, or piping.
```

**refuse:**
```
Repairs that risk fire, flooding, structural collapse, serious injury, or death — or work that legally requires a licensed professional and a permit (e.g., adding circuits or outlets, electrical panel work, gas-line work, major plumbing, removing load-bearing walls, replacing a water heater or main shutoff).
```

---

### Classification approach

*How will the LLM classify the question? Will you give it just the tier definitions, or also examples (few-shot)? Will you ask it to reason step-by-step before naming the tier, or output the tier directly?*

*Consider: what happens when a question is genuinely ambiguous — e.g., "can I replace my own outlets?" Which tier should that land in, and how does your approach handle questions at the boundary?*

```
We will provide the LLM with the precise tier definitions above, a short set of canonical examples (few-shot), and explicit edge-case rules (see prompt below). The model should output the final classification directly in a strict, machine-parseable format (no chain-of-thought). For ambiguous questions: if missing details could plausibly make the task cause severe harm (fire, flood, structural failure, or legally require a permit), default to `refuse`; otherwise default to `caution` and surface the ambiguity in the one-sentence reason.
```

---

### Output format

*How will the LLM communicate the tier and reason back to you? Describe the exact text format you'll ask it to use, so you can parse it reliably.*

*The format you used in Lab 3 (`Label: X / Reasoning: Y`) is a reasonable starting point, but you're not required to use it. Whatever you choose, you'll need to parse it in code — so consider how much variation the LLM might introduce and how you'll handle that.*

```
The LLM must return exactly one JSON object with two keys: `tier` and `reason`. Example (exact format, no surrounding text):

{"tier": "caution", "reason": "Replacing an existing outlet at the same location is usually a like-for-like swap and carries limited risk if power is turned off."}

The `tier` value must be one of: "safe", "caution", "refuse". The `reason` must be a single concise sentence explaining the classification.
```

---

### Prompt structure

*Write the actual prompt you'll use — both the system message and the user message. Don't describe it — write it. Vague prompt descriptions produce vague prompts, which produce inconsistent classifications.*

**System message:**
```
You are a safety-tier classifier for homeowner repair questions. Use the following precise tier definitions and edge-case rules to decide whether a question is `safe`, `caution`, or `refuse`.

Tier definitions:
- safe: Routine maintenance and low-risk repairs that most homeowners can complete with basic hand tools and no permit; worst-case outcomes are cosmetic or minor inconvenience.
- caution: Repairs a motivated homeowner can perform but where mistakes can cause moderate damage or personal injury or involve building systems (water, electrical). Typically like-for-like replacements or repairs confined to existing fixtures, wiring, or piping.
- refuse: Repairs that risk fire, flooding, structural collapse, serious injury, or death — or work that legally requires a licensed professional and a permit (examples: electrical panel work, adding new circuits or outlets, gas-line work, major plumbing, replacing the main water shutoff, removing load-bearing walls, replacing a water heater).

Edge-case rules (apply these before choosing a tier):
- Gas-related questions: always `refuse`.
- "Replace" vs "Add new" for electrical: replacing an existing device at the same location is `caution`; adding new outlets/circuits is `refuse`.
- Wall removal: unless the user confirms a structural engineer or permit says non-load-bearing, classify as `refuse`.
- Water heater replacement: classify as `refuse` unless the user explicitly limits the question to a minor component (anode rod, heating element) and not the full replacement.

Do NOT output internal chain-of-thought. Output only the final classification in the exact JSON format specified by the user message.
```

**User message:**
```
Classify the following homeowner question. Output exactly one JSON object and nothing else, using keys `tier` and `reason` (see format). Use the tier definitions and edge-case rules from the system message.

Question: "{question}"

Few-shot examples (for guidance — your output must still be the exact JSON above):
1) "How do I patch a small hole in drywall?"
=> {"tier": "safe", "reason": "Patching a small drywall hole is routine maintenance with no permit and low risk of injury or major damage."}

2) "How do I replace an outlet that stopped working?"
=> {"tier": "caution", "reason": "Replacing an existing outlet at the same location is a like-for-like swap and carries limited risk if power is isolated."}

3) "How do I add a new outlet in my garage?"
=> {"tier": "refuse", "reason": "Adding a new outlet requires new wiring and possibly opening the electrical panel, which risks fire and typically requires a permit and a licensed electrician."}
```

---

### Caution/refuse boundary

*The most consequential classification decision is whether a question lands in "caution" or "refuse." Write down your rule for this boundary — one sentence. Then give two examples of questions that sit close to the line and explain which side they fall on and why.*

```
Rule: If a mistake could plausibly cause fire, flooding, structural failure, serious injury, death, or the task legally requires a licensed professional/permit, classify as `refuse`; if the worst-case is limited to a broken fixture or cosmetic damage, classify as `safe`; everything in between is `caution`.

Examples near the boundary:
- "Can I replace my own outlets?" — `caution`. The word "replace" implies swapping existing devices in-place; risk is moderate and usually recoverable.
- "Can I add outlets in my garage?" — `refuse`. Adding outlets implies new circuits/wiring and potential work at the panel, which risks fire and requires permits.
```

---

### Fallback behavior

*What does your function return if the LLM response can't be parsed — e.g., if it produces free-form prose instead of your expected format? What happens when tier validation against `VALID_TIERS` fails?*

*Note: failing open (returning "safe" as a fallback) is more dangerous than failing closed (returning "caution"). Which makes more sense here, and why?*

```
If the LLM response cannot be parsed or the returned `tier` is not one of the valid values, the classifier function will fail closed: it will return

{"tier": "caution", "reason": "Classification unclear or unparsable; defaulting to caution for safety and to prompt a clarifying question."}

Additionally, save the raw unparseable LLM output to the audit log for developer review and surface a short clarifying question to the user when appropriate. This avoids failing open (which would return `safe`) because that could lead to dangerous guidance.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 2.*

**One classification that surprised you — question, tier you expected, tier it returned, and why:**

```
[No surprising classifications observed during initial testing. The canonical examples and a handful of ad-hoc test questions were classified as expected:]

- "How do I patch a small hole in drywall?" — expected: "safe"; returned: "safe".
- "How do I replace an outlet that stopped working?" — expected: "caution"; returned: "caution".
- "How do I add a new outlet in my garage?" — expected: "refuse"; returned: "refuse".

These results matched the tier definitions and edge-case rules in the prompt, so no classification surprises required further prompt changes.
```

**One prompt change you made after seeing the first few outputs, and what it fixed:**

```
[I did not change the tier definitions or examples in the prompt itself, but I made a debug change in the code that assembles the prompt:]

- Problem: the few-shot examples contain literal JSON objects with curly braces. I originally inserted the user question with `str.format(...)`, which treated braces in the examples as `format` placeholders and caused a `KeyError` (crash) when assembling the prompt.
- Fix: switched from `user_message = template.format(question=question)` to `user_message = template.replace("{question}", question)`, preserving literal braces in the examples while still inserting the question. This fixed the crash and allowed the LLM to receive the intended few-shot examples unchanged.

No other prompt wording changes were necessary after verifying classification outputs.
```
