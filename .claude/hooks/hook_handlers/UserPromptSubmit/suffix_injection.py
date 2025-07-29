"""Module for injecting suffix instructions into user prompts."""


def get_suffix():
    """Get the suffix to inject as additional context.

    Returns:
        str: The suffix text to add as context
    """
    return (
        "\n<response-requirements>"
        "ALWAYS end your response with a 'Next Steps' section containing exactly 3 actionable suggestions: "
        "1. The most logical immediate next action based on what was just completed "
        "2. A proactive improvement or optimization that could enhance the current work "
        "3. A forward-thinking suggestion that anticipates future needs or potential issues"
        "</response-requirements>"
    )
