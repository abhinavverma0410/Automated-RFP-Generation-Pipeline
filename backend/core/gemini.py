import os
import logging
from google import genai
# google-genai is Google's newest official Python SDK for Gemini
# It replaces the older google-generativeai package
# Install: poetry add google-genai

from google.genai import types
# types contains configuration classes like GenerateContentConfig
# We use it to control temperature, token limits, etc.

from dotenv import load_dotenv
# Loads variables from .env file into os.environ
# Must be called before os.getenv() or the variables won't be available

# Load .env variables into environment
load_dotenv()

# Create logger for this file
logger = logging.getLogger(__name__)


def build_proposal_prompt(tender: dict) -> str:
    """
    Builds a structured prompt from tender data to send to Gemini.

    Why a separate function?
    ------------------------
    The prompt is the most important part of AI generation.
    Keeping it in its own function makes it easy to:
    - Tweak the prompt without touching the API logic
    - Test the prompt output independently
    - Add more tender fields later without changing generate_proposal_draft()

    What makes a good prompt?
    -------------------------
    1. Clear role — tell Gemini what it is
    2. Structured input — give it the tender data cleanly
    3. Explicit output format — tell it exactly what sections to write
    4. Constraints — word limits, tone, what to avoid
    """
    return f"""
You are an expert proposal writer for a Canadian government contracting firm.

Your task is to write a professional bid proposal response for the following tender.

--- TENDER DETAILS ---
Title: {tender['title']}
Reference Number: {tender['reference_number']}
Organization: {tender['organization']}
Closing Date: {tender['closing_date']}
Description: {tender['description']}
Source: {tender['source_link']}

--- INSTRUCTIONS ---
Start the proposal EXACTLY with this formatted header. You MUST leave a blank line between each of these header lines so they render properly in Markdown:

[Your Company Name]

Bid Proposal Response Tender Reference: {tender['reference_number']}

Title: {tender['title']} Organization: {tender['organization']}

Closing Date: {tender['closing_date']}

---

Then, write a structured proposal draft with the following sections:

1. Executive Summary
    - Brief overview of our response and why we are the right fit

2. Understanding of Requirements
    - Demonstrate we understand what the government is asking for

3. Proposed Methodology
    - How we will deliver the work, step by step

4. Relevant Experience
    - Placeholder section noting where past experience would be inserted

5. Compliance Statement
    - Confirm we meet the stated requirements

6. Pricing Placeholder
    - Note that detailed pricing will be provided separately

Keep the tone professional and formal.
Write in clear Canadian English.
Do not invent specific facts — use placeholders where real data would go.
"""


async def generate_proposal_draft(tender: dict) -> str:
    """
    Sends a structured prompt to Gemini and returns the generated proposal draft.

    Why async?
    ----------
    Gemini API calls take time — sometimes several seconds.
    Using async means FastAPI can handle other requests while waiting
    for Gemini to respond, instead of blocking the entire server.

    Parameters
    ----------
    tender : dict
        A dictionary containing tender fields from the database.
        Must include at minimum: title, reference_number, description.

    Returns
    -------
    str
        The full text of the AI-generated proposal draft.

    Raises
    ------
    ValueError  — if GEMINI_API_KEY is missing from .env
    RuntimeError — if the API call fails or returns empty response
    """

    # Read API key from environment variables
    # Never hardcode API keys — always read from .env
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        # Fail immediately with a clear message if key is missing
        # Better to crash early with a useful error than fail silently later
        raise ValueError(
            "GEMINI_API_KEY is missing. Please set it in your .env file."
        )

    # Initialize the Gemini client with our API key
    # genai.Client handles authentication and connection management
    client = genai.Client(api_key=api_key)

    # Build the structured prompt from tender data
    # This separates prompt construction from API call logic
    prompt = build_proposal_prompt(tender)

    logger.info(f"Requesting draft from Gemini for tender: {tender.get('reference_number')}")

    try:
        # client.aio = async interface of the Gemini client
        # .models.generate_content() sends the prompt and returns a response
        # We await it because it's a network call that takes time
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            # gemini-2.5-flash = fast, cost-efficient model
            # good balance of speed and quality for proposal drafting

            contents=prompt,
            # The full prompt string we built above

            config=types.GenerateContentConfig(
                temperature=0.7,
                # temperature controls creativity vs consistency
                # 0.0 = very deterministic, always same output
                # 1.0 = very creative, more varied output
                # 0.7 = balanced — professional but not robotic

                max_output_tokens=8192,
                # Maximum number of tokens (roughly words) in the response
                # 8192 is enough for a detailed multi-section proposal
                # Higher = longer possible output but costs more
            ),
        )

    except Exception as exc:
        # Catch any API errors — network failures, rate limits, auth errors
        # raise...from exc preserves the original error as context
        # so you can see both errors in the traceback
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc

    # Check if Gemini returned actual content
    # Safety filters can cause empty responses without raising an exception
    if not response.text or response.text.strip() == "":
        raise RuntimeError(
            "Gemini returned an empty response. "
            "The prompt may have triggered a safety filter."
        )

    logger.info(f"Draft generated — {len(response.text)} characters")
    return response.text
    # Returns the full proposal draft as a plain string
    # The caller (main.py endpoint) will save this to the Proposal table