from __future__ import annotations

import json

from langchain.agents import create_agent

from agents.state import AseelState
from config.settings import OPENAI_MODEL_UNDERSTANDING
from tools.context_extraction import extract_context
from tools.region_resolution import resolve_region
from utils.location_resolver import location_resolver
from utils.region_override import GENERAL, normalize_region_override
from utils.user_location import (
    canonical_region,
    describe_location,
    normalize_user_location,
)


understanding_agent = create_agent(
    model=OPENAI_MODEL_UNDERSTANDING,
    tools=[],
    system_prompt="""
You are ASEEL's Understanding Agent.

Your job is to understand the user's current question and relevant conversation
memory before retrieval.

You must:

1. Understand the current question.
2. Use conversation memory when the current question is a follow-up.
3. Resolve omitted context and pronouns.
4. Preserve relevant previous city, region, topic, occasion, and role.
5. Give priority to new information from the current question.
6. Create a standalone retrieval_query for the Retrieval Agent.
7. Do not answer the cultural question.
8. Do not invent cultural facts.

A retrieval_query MUST be understandable on its own.
Do not return only a pronoun-based or context-dependent query.

Example:

Previous context:
city: Dammam
region: East
category: Clothes

Current question:
"What about women?"

Correct retrieval_query:
"Traditional clothing for women in Dammam, Eastern Saudi Arabia"

Another example:

Previous context:
city: Jeddah
category: Food

Current question:
"What about breakfast?"

Correct retrieval_query:
"Traditional breakfast foods in Jeddah, Western Saudi Arabia"

LOCATION PRIORITY:

0. If the prompt contains a "Region selection" section, it is the user's explicit
   choice and overrides everything below. Never use any earlier city or region,
   and never add a location the selection does not allow.
1. A city or region explicitly mentioned in the current question always wins.
2. Otherwise, use the location from conversation memory.
3. Only when both are absent, and the prompt contains a "Fallback user location"
   section, use that location.

Never blend the fallback user location with an explicit or remembered location,
and never replace one with it. Never mention that a location was detected or inferred.

Example:

Fallback user location:
Riyadh, Central Saudi Arabia

Current question:
"What is the traditional clothing for women?"

Correct retrieval_query:
"Traditional clothing for women in Riyadh, Central Saudi Arabia"

Return ONLY valid JSON:

{
    "retrieval_query": "...",
    "city": null,
    "region": null,
    "category": null,
    "occasion": null,
    "situation": null,
    "user_role": null,
    "relationship": null,
    "first_time": null,
    "generation": null,
    "formality": null,
    "historical_or_contemporary": null,
    "language": null,
    "intent": null
}
""",
)


def _clean_json(content: str) -> str:
    content = content.strip()

    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    return content.strip()


def _parse_memory(conversation_context: str) -> dict:
    """
    Parse the structured "Conversation memory:" section produced by
    ConversationMemory.to_prompt_context() into a key/value dict.

    Only that section is scanned — not the "Recent conversation:" section
    that may follow it in the combined context built by workflow/graph.py.
    That section is free-form dialogue text, not key/value memory; scanning
    it line-by-line would misread a transcript line like
    "user: What about women?" as a memory field named "user".
    """

    memory = {}

    if not conversation_context:
        return memory

    if "Conversation memory:" in conversation_context:
        section = conversation_context.split("Conversation memory:", 1)[1]
        section = section.split("Recent conversation:", 1)[0]
    else:
        section = conversation_context

    for line in section.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        key = key.strip()
        value = value.strip()

        if key and value:
            memory[key] = value

    return memory


def _resolve_city(
    query: str,
    memory: dict,
    fallback_location: dict | None = None,
) -> str | None:
    location = location_resolver.find_in_query(query)

    if location:
        return location.get("city")

    if memory.get("city"):
        return memory.get("city")

    if fallback_location:
        return fallback_location.get("city")

    return None


def _resolve_region(
    query: str,
    city: str | None,
    memory: dict,
    extracted_region: str | None,
    fallback_region: str | None = None,
) -> str | None:

    direct_region = resolve_region(query)

    if direct_region:
        return direct_region

    if city:
        city_region = resolve_region(city)

        if city_region:
            return city_region

    # Detected user location: only ever set when the question and memory
    # carry no location (see _select_fallback_location), so it is safe to
    # prefer it over the LLM's own guess.
    if fallback_region:
        return fallback_region

    if extracted_region:
        resolved = resolve_region(extracted_region)

        if resolved:
            return resolved

    memory_region = memory.get("region")

    if memory_region:
        resolved = resolve_region(memory_region)

        if resolved:
            return resolved

    return None


def _select_fallback_location(
    query: str,
    memory: dict,
    user_location: dict | None,
) -> dict | None:
    """
    The detected user location is the LAST resort. It is used only when
    (A) the current question names no city/region, and
    (B) conversation memory holds no city/region either.
    (A UI-selected region is appended to the question text by the frontend,
    so it is caught by (A).)
    """
    if not user_location:
        return None

    if location_resolver.find_in_query(query) or resolve_region(query):
        return None

    memory_region = (memory.get("region") or "").strip().lower()

    if memory.get("city") or (memory_region and memory_region != "general"):
        return None

    return user_location


def _drop_stale_city(
    query: str,
    city: str | None,
    memory: dict,
) -> str | None:
    """
    A remembered city must not survive when the current question explicitly
    names a different region (e.g. memory holds a detected Riyadh, then the
    user picks East in the UI). Without this, city and region would disagree.
    """
    if not city or location_resolver.find_in_query(query):
        return city

    explicit_region = canonical_region(resolve_region(query))

    if not explicit_region:
        return city

    known = location_resolver.resolve(city)
    city_region = canonical_region(known.get("planning_region")) if known else None

    if city_region and city_region != explicit_region:
        return None

    return city


def _ensure_location_in_query(
    retrieval_query: str,
    fallback_location: dict | None,
) -> str:
    """
    Deterministic backstop: if the fallback location is active but the LLM did
    not put it into retrieval_query, append it.
    """
    if not fallback_location:
        return retrieval_query

    lowered = retrieval_query.lower()
    tokens = []

    city = (fallback_location.get("city") or "").lower()
    if city:
        tokens.append(city)
        if city.endswith(" city"):
            tokens.append(city[:-5])

    region = (fallback_location.get("region") or "").lower()
    if region:
        tokens.append(region)

    if any(token and token in lowered for token in tokens):
        return retrieval_query

    return f"{retrieval_query} in {describe_location(fallback_location)}"


def _strip_location_from_context(conversation_context: str) -> str:
    """
    Drop the remembered city/region lines from the "Conversation memory:"
    section. Used when the user made an explicit region selection in the UI,
    so remembered locations cannot leak into that request. Other memory fields
    (category, occasion, role, ...) and the "Recent conversation:" text stay.
    """
    if not conversation_context or "Conversation memory:" not in conversation_context:
        return conversation_context

    head, rest = conversation_context.split("Conversation memory:", 1)

    if "Recent conversation:" in rest:
        memory_section, tail = rest.split("Recent conversation:", 1)
        tail = "Recent conversation:" + tail
    else:
        memory_section, tail = rest, ""

    kept = [
        line
        for line in memory_section.splitlines()
        if line.split(":", 1)[0].strip().lower() not in {"city", "region"}
    ]

    return f"{head}Conversation memory:" + "\n".join(kept) + "\n" + tail


def _city_for_override(query: str, region_override: str) -> str | None:
    """
    City under an explicit UI region selection. Only a city typed in the CURRENT
    question can survive, and only if it belongs to the selected region.
    Memory and detected locations never contribute. General has no city.
    """
    if region_override == GENERAL:
        return None

    found = location_resolver.find_in_query(query)

    if not found:
        return None

    city = found.get("city")
    known = location_resolver.resolve(city) if city else None
    city_region = (
        canonical_region(known.get("planning_region")) if known else None
    )

    if city_region and city_region == canonical_region(region_override):
        return city

    return None


def _specific_region(text: str) -> str | None:
    """Canonical region named in text, ignoring nationwide/'General' wording."""
    region = canonical_region(resolve_region(text))

    if region and str(region).strip().lower() != "general":
        return region

    return None


def _apply_override_to_query(
    retrieval_query: str,
    query: str,
    region_override: str,
    category,
    occasion,
    situation,
    user_role,
) -> str:
    """
    Deterministic backstop for an explicit UI region selection. The LLM builds
    retrieval_query from conversation context and can drag in an old city or
    region; region matching must never depend on the LLM.
    """
    if region_override == GENERAL:
        names_location = (
            location_resolver.find_in_query(retrieval_query)
            or _specific_region(retrieval_query)
        )
        user_named_location = (
            location_resolver.find_in_query(query) or _specific_region(query)
        )

        if names_location and not user_named_location:
            return _build_fallback_query(
                query=query,
                city=None,
                region=None,
                category=category,
                occasion=occasion,
                situation=situation,
                user_role=user_role,
            )

        return retrieval_query

    target = canonical_region(region_override)

    named = set()

    mentioned = _specific_region(retrieval_query)
    if mentioned:
        named.add(mentioned)

    found = location_resolver.find_in_query(retrieval_query)
    if found:
        known = location_resolver.resolve(found.get("city"))
        found_region = (
            canonical_region(known.get("planning_region")) if known else None
        )
        if found_region:
            named.add(found_region)

    if named - {target}:
        return _build_fallback_query(
            query=query,
            city=None,
            region=region_override,
            category=category,
            occasion=occasion,
            situation=situation,
            user_role=user_role,
        )

    if not named:
        return f"{retrieval_query} in the {region_override} region of Saudi Arabia"

    return retrieval_query


def _get_value(
    extracted: dict,
    basic_context: dict,
    memory: dict,
    key: str,
):
    """
    Resolve one context field, preferring the deterministic source when
    one exists for that field.

    For fields context_extraction.py can actually detect (category,
    occasion, user_role), the regex-based basic_context is the source of
    truth — it can only return a value that is literally present as a
    keyword in the text, so it can't hallucinate. The LLM's own guess for
    these fields is used only as a fallback, when the deterministic
    extractor found nothing (e.g. the keyword is implied but not literally
    present in the current query or memory text).

    For fields with no deterministic extractor at all (situation,
    relationship, first_time, generation, formality,
    historical_or_contemporary, language), the LLM is the only source
    available, so its output is used directly.
    """

    deterministic_fields = {"category", "occasion", "user_role"}

    if key in deterministic_fields:
        value = basic_context.get(key)

        if value not in (None, "", []):
            return value

        value = extracted.get(key)

        if value not in (None, "", []):
            return value

        return memory.get(key)

    # No deterministic extractor for this field — trust the LLM first.
    value = extracted.get(key)

    if value not in (None, "", []):
        return value

    value = basic_context.get(key)

    if value not in (None, "", []):
        return value

    return memory.get(key)


def _build_fallback_query(
    query: str,
    city: str | None,
    region: str | None,
    category: str | None,
    occasion: str | None,
    situation: str | None,
    user_role: str | None,
) -> str:

    parts = [query]

    context = [
        category,
        occasion,
        situation,
        user_role,
        city,
        region,
    ]

    for value in context:
        if value and value not in parts:
            parts.append(str(value))

    return " ".join(parts)


def understand_context(state: AseelState) -> dict:

    query = state.get("query", "")

    # Explicit UI region selection (including "General"); None = Auto.
    region_override = normalize_region_override(state.get("region_override"))

    conversation_context = state.get(
        "conversation_context",
        "",
    )

    memory = _parse_memory(
        conversation_context,
    )

    # An explicit region overrides a conflicting remembered location,
    # but keeps a remembered city when it belongs to the selected region.
    # Example: memory=Riyadh/Central + UI=Central -> keep Riyadh.
    if region_override:
        remembered_region = canonical_region(memory.get("region"))

        if region_override == GENERAL:
            conversation_context = _strip_location_from_context(
                conversation_context
            )
            memory = _parse_memory(conversation_context)
        elif remembered_region and remembered_region != region_override:
            conversation_context = _strip_location_from_context(
                conversation_context
            )
            memory = _parse_memory(conversation_context)

    basic_context = extract_context(
        query=query,
        conversation_context=conversation_context,
    )

    # An explicit selection (a region OR General) beats the detected location.
    user_location = (
        None
        if region_override
        else normalize_user_location(state.get("user_location"))
    )

    fallback_location = _select_fallback_location(
        query,
        memory,
        user_location,
    )

    location_block = ""

    if fallback_location:
        location_block = (
            "\nFallback user location (automatically detected):\n"
            f"{describe_location(fallback_location)}\n\n"
            "The current question and the conversation memory contain no location.\n"
            "Use this location in retrieval_query. Do not mention that it was detected.\n"
        )

    override_block = ""

    if region_override == GENERAL:
        override_block = (
            "\nRegion selection (explicit user choice, overrides everything else):\n"
            "GENERAL - nationwide scope.\n"
            "Do NOT add any city or region to retrieval_query and ignore any city "
            "or region mentioned earlier. Set city and region to null.\n"
        )
    elif region_override:
        override_block = (
            "\nRegion selection (explicit user choice, overrides everything else):\n"
            f"{region_override} region of Saudi Arabia.\n"
            "Use only this region in retrieval_query and ignore any other city "
            "or region mentioned earlier.\n"
        )

    user_prompt = f"""
Conversation memory:
{conversation_context or "None"}

Current user question:
{query}
{location_block}{override_block}
Basic extracted context:
{json.dumps(basic_context, ensure_ascii=False)}

Create the final structured context.

Important:
- If this is a follow-up question, use the previous memory.
- Keep the current question's new information.
- Preserve the previous city, topic, occasion, and role when the user does not change them.
- Build a complete standalone retrieval_query.
- The retrieval_query must contain enough context for retrieval even if the
  current question contains pronouns such as "it", "they", "what about", etc.
- Never return only the short follow-up question as retrieval_query.
"""

    extracted = {}

    try:
        result = understanding_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ]
            }
        )

        messages = result.get(
            "messages",
            [],
        )

        for message in reversed(messages):
            content = getattr(
                message,
                "content",
                "",
            )

            if not content:
                continue

            try:
                extracted = json.loads(
                    _clean_json(content)
                )
                break
            except Exception:
                continue

    except Exception:
        extracted = {}

    if region_override:
        city = _city_for_override(query, region_override)
    else:
        city = _resolve_city(
            query,
            memory,
            fallback_location,
        )

        city = _drop_stale_city(
            query,
            city,
            memory,
        )

    category = _get_value(
        extracted,
        basic_context,
        memory,
        "category",
    )

    occasion = _get_value(
        extracted,
        basic_context,
        memory,
        "occasion",
    )

    situation = _get_value(
        extracted,
        basic_context,
        memory,
        "situation",
    )

    user_role = _get_value(
        extracted,
        basic_context,
        memory,
        "user_role",
    )

    relationship = _get_value(
        extracted,
        basic_context,
        memory,
        "relationship",
    )

    first_time = _get_value(
        extracted,
        basic_context,
        memory,
        "first_time",
    )

    generation = _get_value(
        extracted,
        basic_context,
        memory,
        "generation",
    )

    formality = _get_value(
        extracted,
        basic_context,
        memory,
        "formality",
    )

    historical_or_contemporary = _get_value(
        extracted,
        basic_context,
        memory,
        "historical_or_contemporary",
    )

    language = _get_value(
        extracted,
        basic_context,
        memory,
        "language",
    )

    # Explicit UI selection wins outright; otherwise the normal priority applies.
    region = region_override or _resolve_region(
        query=query,
        city=city,
        memory=memory,
        extracted_region=extracted.get("region"),
        fallback_region=(
            fallback_location.get("region") if fallback_location else None
        ),
    )

    retrieval_query = str(
        extracted.get("retrieval_query", "")
    ).strip()

    if (
        not retrieval_query
        or retrieval_query.lower() == query.strip().lower()
    ):
        retrieval_query = _build_fallback_query(
            query=query,
            city=city,
            region=region,
            category=category,
            occasion=occasion,
            situation=situation,
            user_role=user_role,
        )

    retrieval_query = _ensure_location_in_query(
        retrieval_query,
        fallback_location,
    )

    if region_override:
        retrieval_query = _apply_override_to_query(
            retrieval_query,
            query,
            region_override,
            category=category,
            occasion=occasion,
            situation=situation,
            user_role=user_role,
        )

    if region_override:
        location_source = "ui_selection"
    elif fallback_location:
        location_source = "user_location"
    elif location_resolver.find_in_query(query) or resolve_region(query):
        location_source = "query"
    elif city or region:
        location_source = "memory"
    else:
        location_source = None

    return {
        "retrieval_query": retrieval_query,
        "city": city,
        "region": region,
        "category": category,
        "occasion": occasion,
        "situation": situation,
        "user_role": user_role,
        "relationship": relationship,
        "first_time": first_time,
        "generation": generation,
        "formality": formality,
        "historical_or_contemporary": historical_or_contemporary,
        "language": language,
        "intent": extracted.get(
            "intent",
            basic_context.get("intent"),
        ),
        "location_source": location_source,
        "region_override": region_override,
        "attempts": state.get(
            "attempts",
            0,
        ),
    }


understand_query = understand_context










# from __future__ import annotations

# from langchain.agents import create_agent
# from langchain_core.tools import tool

# from agents.state import AseelState
# from config.settings import OPENAI_MODEL
# from tools.context_extraction import extract_context
# from tools.region_resolution import resolve_region
# from retrieval.vector_store import CulturalVectorStore


# @tool
# def extract_user_context(query: str, conversation_context: str = "") -> dict:
#     """Extract cultural context such as occasion, user role, category, and intent from the user's query."""
#     return extract_context(query, conversation_context)


# @tool
# def resolve_user_region(query: str) -> str | None:
#     """Resolve the Saudi region mentioned or implied by the user's query."""

#     region = resolve_region(query)

#     return CulturalVectorStore.normalize_region(region)


# understanding_agent = create_agent(
#     model=OPENAI_MODEL,
#     tools=[
#         extract_user_context,
#         resolve_user_region,
#     ],
#     system_prompt = """
# You are ASEEL's Understanding Agent.

# Your responsibility is to analyze the user's question and extract the
# information needed by the downstream retrieval and validation agents.

# You are NOT a cultural knowledge agent.
# You must NOT answer the user's question or provide cultural facts.
# Your job is to understand the request accurately and produce structured
# context for retrieval.

# CORE OBJECTIVE:
# Convert the user's natural-language question into accurate, retrieval-ready
# context while preserving the user's original intent.

# 1. INTENT UNDERSTANDING
# - Identify what the user is actually asking.
# - Determine the main topic, question type, and situation.
# - Preserve the meaning and scope of the original question.
# - Do not rewrite the question in a way that changes its meaning.
# - Distinguish between asking about a fact, custom, tradition, etiquette,
#   behavior, clothing, food, occasion, social interaction, or other cultural
#   topic when possible.

# 2. CONTEXT EXTRACTION
# - ALWAYS use the context extraction tool when processing the query.
# - Extract information from the user's message AND relevant information from
#   the conversation context.
# - The conversation context may contain previously established information
#   such as city, region, occasion, situation, relationship, first-time status,
#   topic, or other relevant constraints.
# - If the current question is a follow-up or refers to something previously
#   discussed using words such as "what about", "also", "and", "there", "that",
#   "they", or similar references, use the relevant previous context to
#   interpret the question.
# - Reuse previously established context when the user has not changed it.
# - A new explicit value from the current user message overrides the previous
#   value for that field.
# - Do NOT invent new information that is not present in either the current
#   query or the relevant conversation context.

# 3. LOCATION RESOLUTION
# - ALWAYS use the region resolution tool when a location is mentioned or can
#   be resolved.
# - Convert recognized Saudi cities or locations into ASEEL's canonical
#   planning-region labels.
# - The ONLY valid canonical regions are:
#   South, North, East, West, Central, General.
# - Preserve the user's original city/location separately when available.
# - Do not replace a city with a region and lose the original city information.
# - If the location cannot be reliably resolved, use General or unknown as
#   appropriate rather than guessing.
# - Never infer a region from unrelated context.

# 4. LOCATION PRECISION
# Use the most specific location information available.

# For example:
# User says "What do people do in Dammam?"
# → city = Dammam
# → region = East

# User says "What is common in the Western region?"
# → region = West

# User says "What is this custom in Saudi Arabia?"
# → region = General

# Do not convert a specific city request into a nationwide request.

# 5. LANGUAGE
# - Detect the language of the user's question.
# - Preserve the original language information for downstream processing.
# - Do not translate or alter the user's intent unless required by a tool.
# - If the question is multilingual or contains mixed languages, preserve the
#   meaning of all relevant parts.

# 6. AMBIGUITY
# - Do not resolve ambiguity using assumptions.
# - If multiple interpretations are possible, preserve the ambiguity and record
#   it when relevant.
# - If clarification is genuinely required to perform accurate retrieval,
#   indicate the missing information.
# - Do not invent an answer to resolve an ambiguous question.

# 7. RETRIEVAL PREPARATION
# Create a concise retrieval-oriented representation of the query.

# For follow-up questions, combine the current question with relevant
# previous context so that the Retrieval Agent can understand the complete
# request independently.

# For example:

# Previous context:
# city = Dammam
# region = East
# topic = traditional clothing
# gender = men

# Current query:
# "What about women?"

# Retrieval-oriented representation:
# "Traditional clothing for women in Dammam, Eastern Region of Saudi Arabia."

# The retrieval context should contain:
# - original user question
# - normalized intent
# - topic
# - location/city
# - canonical region
# - relevant cultural context
# - language
# - important constraints
# - missing or ambiguous information when applicable

# Do not add cultural knowledge to improve the retrieval query.
# Only combine information that is explicitly available from the current query
# or relevant conversation context.

# Do not add cultural knowledge to improve the retrieval query.

# 8. BOUNDARIES
# - Do NOT retrieve cultural knowledge yourself unless required through the
#   specified understanding tools.
# - Do NOT decide whether retrieved evidence is correct.
# - Do NOT calculate evidence confidence.
# - Do NOT validate cultural claims.
# - Do NOT generate the final answer.
# - Do NOT use general model knowledge to fill missing information.

# 9. OUTPUT QUALITY
# Return clear, structured context for downstream agents.

# The output should make it easy for the Retrieval Agent to understand:
# "What exactly is the user asking, where does it apply, and what context matters?"

# Before returning the result, verify:
# - Did I preserve the user's original intent?
# - Did I avoid inventing missing information?
# - Did I preserve the specific city/location?
# - Did I resolve the canonical region correctly when possible?
# - Did I identify relevant context?
# - Did I avoid adding cultural claims?
# - Is the output useful for retrieval?

# Return only the extracted and normalized context.
# Do not provide the final cultural answer.
# """,
# )


# def understand_context(state: AseelState) -> dict:
#     query = state["query"]
#     conversation_context = state.get("conversation_context", "")

#     result = understanding_agent.invoke(
#         {
#             "messages": [
#                 {
#                     "role": "user",
#                     "content": f"""
# Understand this ASEEL user request.

# User query:
# {query}

# Conversation context:
# {conversation_context or "None"}

# Use the available tools to extract the context and resolve the region.
# """,
#                 }
#             ]
#         }
#     )

#     messages = result.get("messages", [])

#     extracted_context = {}
#     agent_region = None

#     for message in messages:
#         if getattr(message, "type", None) != "tool":
#             continue

#         tool_name = getattr(message, "name", "")
#         content = message.content

#         if tool_name == "extract_user_context":

#             if isinstance(content, dict):
#                 extracted_context = content
#             else:
#                 try:
#                     import json
#                     extracted_context = json.loads(content)
#                 except (TypeError, ValueError):
#                     pass

#         elif tool_name == "resolve_user_region":

#             agent_region = content if content else None

#     # IMPORTANT:
#     # Resolve the region deterministically from the original user query.
#     # Do not rely on the LLM's interpretation when an explicit region exists.
#     detected_region = resolve_region(query)

#     if detected_region:
#         region = CulturalVectorStore.normalize_region(detected_region)
#     else:
#         region = CulturalVectorStore.normalize_region(agent_region)

#     return {
#         **extracted_context,
#         "region": region,
#         "attempts": state.get("attempts", 0),
#         "retrieval_query": query,
#     }