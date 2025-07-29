"""Module for injecting Zen consultation instructions into user prompts."""

import os
import re
import sys
from pathlib import Path

# Use direct import as primary method
sys.path.append(str(Path(__file__).parent))
from smart_filter import should_use_zen_smart

# Try to load environment variables
try:
    from dotenv import load_dotenv

    # Load .env file from project root
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    # If python-dotenv is not installed, continue without it
    pass


def get_available_agents():
    """Get list of available agents from .claude/agents directory.

    Returns:
        list: List of tuples (agent_name, brief_description)
    """
    agents = []

    # Try to get project directory from environment variable
    project_dir = os.getenv("PROJECT_DIR")

    if project_dir:
        # Use environment variable path
        agents_dir = Path(project_dir) / ".claude" / "agents"
    else:
        # Fallback to absolute path
        agents_dir = Path("/home/devcontainers/better-claude/.claude/agents")

    if not agents_dir.exists():
        return agents

    for agent_file in agents_dir.glob("*.md"):
        try:
            content = agent_file.read_text()
            # Extract name and description from YAML frontmatter
            name_match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
            desc_match = re.search(
                r"^description:\s*(.+?)(?=\n(?:tools:|color:|Examples:|examples:))",
                content,
                re.MULTILINE | re.DOTALL,
            )

            if name_match and desc_match:
                name = name_match.group(1).strip()
                # Get first sentence of description for brevity
                desc = desc_match.group(1).strip()
                first_sentence = f"{desc.split('.')[0]}."
                agents.append((name, first_sentence))
        except Exception:
            # Skip files that can't be parsed
            continue

    return agents


def _analyze_zen_tool_needs(user_prompt):
    """Analyze user prompt to determine best ZEN tools to recommend.
    
    Returns:
        tuple: (primary_tool, secondary_tools, reasoning)
    """
    prompt_lower = user_prompt.lower()
    
    # Tool recommendation patterns
    tool_patterns = {
        'thinkdeep': {
            'patterns': [r'\b(investigate|complex|deep|thorough|comprehensive|analyze deeply|root cause|why does|understand how)\b',
                        r'\b(architecture|system|design pattern|investigation|research)\b'],
            'description': 'Deep investigation & systematic reasoning'
        },
        'debug': {
            'patterns': [r'\b(debug|bug|error|issue|problem|broken|failing|fix|troubleshoot)\b',
                        r'\b(exception|crash|not working|wrong|incorrect)\b'],
            'description': 'Systematic debugging & root cause analysis'
        },
        'analyze': {
            'patterns': [r'\b(analyze|assessment|review|evaluate|examine|audit)\b',
                        r'\b(performance|quality|architecture|code review|maintainability)\b'],
            'description': 'Code analysis & architecture assessment'
        },
        'consensus': {
            'patterns': [r'\b(should I|which is better|compare|decide|choice|opinion|recommend)\b',
                        r'\b(versus|vs|alternative|option|approach|strategy)\b'],
            'description': 'Multi-model decision making & expert consensus'
        },
        'chat': {
            'patterns': [r'\b(help|how to|explain|guide|question|brainstorm|discuss)\b',
                        r'\b(idea|concept|clarify|understand|learn)\b'],
            'description': 'General consultation & brainstorming'
        }
    }
    
    # Score each tool
    tool_scores = {}
    for tool, data in tool_patterns.items():
        score = 0
        for pattern in data['patterns']:
            matches = len(re.findall(pattern, prompt_lower))
            score += matches
        if score > 0:
            tool_scores[tool] = score
    
    if not tool_scores:
        return 'chat', [], 'general_consultation'
    
    # Get primary tool (highest score)
    primary_tool = max(tool_scores.items(), key=lambda x: x[1])[0]
    
    # Get secondary tools (other high scores)
    secondary_tools = [tool for tool, score in tool_scores.items() 
                      if tool != primary_tool and score >= max(1, tool_scores[primary_tool] * 0.5)]
    
    reasoning = f"Primary: {primary_tool} (score: {tool_scores[primary_tool]})"
    if secondary_tools:
        reasoning += f", Secondary: {', '.join(secondary_tools)}"
    
    return primary_tool, secondary_tools[:2], reasoning  # Limit to 2 secondary tools


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

    # Analyze which ZEN tools would be most helpful
    primary_tool, secondary_tools, tool_reasoning = _analyze_zen_tool_needs(user_prompt)
    
    # Get available agents
    agents = get_available_agents()
    agents_list = "\n".join([f"- {name}: {desc}" for name, desc in agents])

    # Build tool recommendations
    tool_recommendations = f"PRIMARY: mcp__zen__{primary_tool}"
    if secondary_tools:
        secondary_list = ", ".join([f"mcp__zen__{tool}" for tool in secondary_tools])
        tool_recommendations += f" | SECONDARY: {secondary_list}"
    
    # Enhanced instruction with multiple tool options
    return (
        f"<system-instruction>ZEN_CONSULTATION_RECOMMENDED: Based on analysis, use "
        f"{tool_recommendations} with parameters {{use_websearch: true, model: 'auto', "
        f"prompt: 'User request: {user_prompt[:200] + '...' if len(user_prompt) > 200 else user_prompt}'}}. "
        f"Then consider 0-3 specialized subagents from: {agents_list}. "
        f"Tool selection reasoning: {tool_reasoning} | "
        f"Complexity score: {metadata['score']:.2f}</system-instruction> "
    )
