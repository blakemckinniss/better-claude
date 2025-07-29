"""Module for injecting Zen consultation instructions into user prompts."""

from .smart_filter import should_use_zen_smart


def get_zen_injection(user_prompt=None):
    """Get the Zen instruction to inject as additional context.

    Args:
        user_prompt: Optional user prompt to filter against

    Returns:
        str: The Zen consultation instruction or empty string
    """
    if not user_prompt:
        return ""

    # Use smart filter for intelligent decision
    should_use, metadata = should_use_zen_smart(user_prompt)

    if not should_use:
        # Log decision for debugging if needed
        # print(f"Zen skipped: {metadata['reasoning']} (score: {metadata['score']:.2f})")
        return ""

    # Include reasoning in the instruction for transparency
    return (
        f"<system-instruction>BEFORE_RESPONSE: Execute mcp__zen__* with parameters "
        f"{{use_websearch: true, model: 'auto', prompt: 'Provide expert analysis and perspectives for the following user request'}} "
        f"[complexity_score: {metadata['score']:.2f}]</system-instruction> "
    )
