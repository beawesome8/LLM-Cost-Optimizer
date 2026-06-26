import re


# -----------------------------------------------------------------------
# FILLER PHRASES
#
# These are polite human phrases that add zero value for an LLM.
# Claude does not need "please" to understand an instruction.
# Removing them reduces token count at zero quality cost.
#
# Each entry is a "regex pattern":
# \s* means "zero or more spaces after this phrase"
# re.IGNORECASE means we catch "Please", "please", "PLEASE" all the same
# -----------------------------------------------------------------------
FILLER_PHRASES = [
    r"could you please\s*",
    r"please can you\s*",
    r"i was wondering if you could\s*",
    r"i would like you to\s*",
    r"can you please\s*",
    r"would you be able to\s*",
    r"i need you to\s*",
    r"kindly\s*",
    r"if you don't mind\s*",
    r"if you do not mind\s*",
    r"as an ai language model,?\s*",
    r"as an ai,?\s*",
    r"certainly!\s*",
    r"of course!\s*",
    r"sure!\s*",
    r"please\s*",
]


def remove_filler_phrases(text: str) -> str:
    """
    Remove common filler phrases from the prompt.

    Iterates through every filler pattern and removes it from the text.
    Uses re.sub() which means "substitute this pattern with nothing".

    Example:
        Input  → "Could you please summarize this article for me?"
        Output → "summarize this article for me?"

    Args:
        text: The raw prompt from the user.

    Returns:
        str: The prompt with filler phrases removed.
    """
    for phrase in FILLER_PHRASES:
        text = re.sub(phrase, "", text, flags=re.IGNORECASE)
    return text


def normalize_whitespace(text: str) -> str:
    """
    Clean up extra spaces, tabs, and blank lines.

    Every whitespace character costs tokens.
    Two spaces is the same as one space to Claude — but costs more.

    What this fixes:
        "Summarize    this    text"  → "Summarize this text"
        "Hello\n\n\n\nWorld"        → "Hello\n\nWorld"
        "  leading and trailing  "  → "leading and trailing"

    Args:
        text: The prompt text.

    Returns:
        str: Cleaned text with normalized whitespace.
    """

    # Replace 2+ spaces with a single space
    text = re.sub(r" {2,}", " ", text)

    # Replace 3+ newlines with just 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove spaces at the very start and end
    text = text.strip()

    return text


def remove_repeated_sentences(text: str) -> str:
    """
    Remove duplicate sentences from the prompt.

    Sometimes users accidentally paste the same instruction twice.
    We split by sentence endings, deduplicate, then rejoin.

    Example:
        Input  → "Summarize this. Make it short. Summarize this."
        Output → "Summarize this. Make it short."

    Args:
        text: The prompt text.

    Returns:
        str: Prompt with duplicate sentences removed.
    """

    # Split into sentences at . ! or ? followed by a space
    sentences = re.split(r'(?<=[.!?])\s+', text)

    seen = set()
    unique_sentences = []

    for sentence in sentences:
        # Normalize for comparison — lowercase and strip spaces
        # This means "Summarize this." and "summarize this." are the same
        normalized = sentence.lower().strip()

        if normalized not in seen:
            seen.add(normalized)
            unique_sentences.append(sentence)

    return " ".join(unique_sentences)


def estimate_tokens(text: str) -> int:
    """
    Estimate how many tokens a piece of text will use.

    We do not have access to Claude's exact tokenizer here.
    The reliable rule of thumb is: 1 token ≈ 4 characters in English.

    This is an ESTIMATE. Good enough for cost planning and reporting.
    The actual token count comes back from Anthropic in the response.

    Args:
        text: Any text string.

    Returns:
        int: Estimated token count. Minimum 1 (never 0).
    """
    return max(1, len(text) // 4)


def optimize_prompt(prompt: str) -> dict:
    """
    Run all optimization steps on a prompt and return the results.

    This is the MAIN function that the rest of the app calls.
    It runs every step in sequence and returns both the cleaned
    prompt AND a report of how much was saved.

    Steps in order:
        1. Remove filler phrases
        2. Remove repeated sentences
        3. Normalize whitespace

    Args:
        prompt: The raw prompt from the user.

    Returns:
        dict: {
            "original_prompt"  : the untouched original,
            "optimized_prompt" : the cleaned version to send to Claude,
            "tokens_before"    : estimated tokens before optimization,
            "tokens_after"     : estimated tokens after optimization,
            "tokens_saved"     : tokens_before - tokens_after,
            "percent_saved"    : percentage of tokens removed
        }

    Example:
        Input  → "Could you please summarize    this article?\n\n\n"
        Output → {
            "optimized_prompt": "summarize this article?",
            "tokens_saved": 6,
            "percent_saved": 46.15
        }
    """

    # Count tokens BEFORE we touch anything
    tokens_before = estimate_tokens(prompt)

    # Run each optimization step in sequence
    # Order matters: remove phrases first, then deduplicate, then whitespace
    optimized = prompt
    optimized = remove_filler_phrases(optimized)
    optimized = remove_repeated_sentences(optimized)
    optimized = normalize_whitespace(optimized)

    # Count tokens AFTER optimization
    tokens_after = estimate_tokens(optimized)

    # Calculate how much we saved
    tokens_saved = tokens_before - tokens_after
    percent_saved = (
        round((tokens_saved / tokens_before) * 100, 2)
        if tokens_before > 0
        else 0.0
    )

    return {
        "original_prompt": prompt,
        "optimized_prompt": optimized,
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "tokens_saved": tokens_saved,
        "percent_saved": percent_saved
    }