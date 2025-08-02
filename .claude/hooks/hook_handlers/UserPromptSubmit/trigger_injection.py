"""Module for injecting MCP tool instructions based on keyword triggers."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Default keyword mappings with priorities
DEFAULT_MCP_MAPPINGS: Dict[str, Dict] = {
    "mcp__github__": {
        "name": "GitHub MCP",
        "priority": 8,
        "keywords": {
            # High priority (exact tool references)
            10: ["github", "gh cli", "github api"],
            # Medium-high priority (specific actions)
            8: ["pull request", "create pr", "merge pr", "github issue", "create issue"],
            # Medium priority (git operations)
            6: ["git commit", "git push", "git merge", "fork repo", "clone repo"],
            # Lower priority (general terms)
            4: ["repository", "repo", "git", "branch", "contributor", "collaborator"],
            # CI/CD keywords
            7: ["github actions", "github workflow", "ci/cd pipeline", "deploy github"]
        },
        "negative_patterns": [
            r"no issue", r"not an issue", r"without github", r"avoid github",
            r"don't.*github", r"not.*repository", r"fake repo"
        ]
    },
    "mcp__zen__": {
        "name": "ZEN Strategic AI",
        "priority": 9,
        "keywords": {
            # Highest priority (explicit requests)
            10: ["use zen", "consult zen", "zen analysis", "brainstorm"],
            # High priority (complex analysis)
            9: ["analyze architecture", "analyze the architecture", "debug complex", "root cause analysis", "deep dive"],
            # Medium priority (planning & strategy)
            7: ["plan implementation", "design strategy", "architect solution", "technical roadmap"],
            # Medium priority (review & assessment)
            6: ["code review", "security audit", "performance analysis", "evaluate design"],
            # Lower priority (general terms)
            4: ["complex problem", "challenging task", "multi-step process", "brainstorm"],
            # Testing strategy
            8: ["test strategy", "test plan", "generate tests", "test coverage analysis"],
            # DevOps & CI/CD
            5: ["ci/cd strategy", "deployment plan", "infrastructure design", "scaling strategy"]
        },
        "negative_patterns": [
            r"simple", r"trivial", r"basic", r"easy", r"straightforward",
            r"no analysis needed", r"skip review"
        ]
    },
    "mcp__filesystem__": {
        "name": "File System Operations",
        "priority": 7,
        "keywords": {
            # High priority (specific operations)
            9: ["create file", "delete file", "move file", "copy file", "rename file"],
            # Medium-high priority (directory operations)
            8: ["mkdir", "create folder", "create directory", "list files", "directory tree"],
            # Medium priority (search operations)
            6: ["find files", "search files", "file glob", "file pattern"],
            # Lower priority (general terms)
            4: ["file system", "folder structure", "file path"],
            # DevOps related
            7: ["config files", "env files", "dotfiles", "project structure"]
        },
        "negative_patterns": [
            r"filing cabinet", r"file lawsuit", r"single file line"
        ]
    },
    "mcp__tavily-remote__": {
        "name": "Web Search & Extraction",
        "priority": 8,
        "keywords": {
            # Highest priority (explicit search)
            10: ["search web", "search the web", "google search", "web search", "search online"],
            # High priority (documentation)
            8: ["find documentation", "latest docs", "api reference", "official docs"],
            # Medium priority (research)
            6: ["research topic", "current information", "latest news", "find tutorial"],
            # Content extraction
            9: ["extract from url", "scrape website", "fetch content", "crawl site"],
            # Stack Overflow & forums
            7: ["stack overflow", "forum post", "community answer", "developer forum"]
        },
        "negative_patterns": [
            r"search code", r"search files", r"internal search", r"database search"
        ]
    },
    "mcp__playwright__": {
        "name": "Browser Automation",
        "priority": 7,
        "keywords": {
            # Highest priority (explicit automation)
            10: ["browser automation", "automate browser", "web automation"],
            # High priority (testing)
            9: ["e2e test", "end to end test", "ui test", "browser test"],
            # Medium priority (specific tools)
            7: ["playwright", "puppeteer", "selenium", "webdriver"],
            # Actions
            6: ["click button", "fill form", "take screenshot", "wait for element"],
            # Testing scenarios
            8: ["test user flow", "test login", "test checkout", "visual regression"]
        },
        "negative_patterns": [
            r"manual test", r"unit test", r"api test"
        ]
    },
    "mcp__context7__": {
        "name": "Library Documentation",
        "priority": 7,
        "keywords": {
            # Framework specific (highest priority)
            9: ["react docs", "react documentation", "vue docs", "angular docs", "nextjs docs", "django docs"],
            # Library specific
            8: ["numpy reference", "pandas api", "express guide", "fastapi docs"],
            # Package managers
            6: ["npm package", "pypi package", "cargo crate", "composer package"],
            # General
            5: ["library documentation", "framework guide", "api reference"],
            # Version specific
            7: ["latest version", "migration guide", "breaking changes", "upgrade guide"]
        },
        "negative_patterns": [
            r"internal docs", r"company documentation"
        ]
    },
    "mcp__shadcn-ui__": {
        "name": "shadcn/ui Components",
        "priority": 6,
        "keywords": {
            # Explicit reference
            10: ["shadcn", "shadcn ui", "shadcn component"],
            # Specific components
            8: ["dialog component", "modal component", "dropdown component", "toast component"],
            # UI patterns
            7: ["data table component", "command palette", "form component", "card component"],
            # Styling
            6: ["tailwind component", "dark mode toggle", "theme switcher"],
            # Accessibility
            5: ["accessible component", "aria component", "keyboard navigation"]
        },
        "negative_patterns": []
    },
    "mcp___magicuidesign_mcp__": {
        "name": "Magic UI Components",
        "priority": 6,
        "keywords": {
            # Explicit reference
            10: ["magic ui", "magic design", "magic component"],
            # Effects
            9: ["particle effect", "confetti animation", "sparkle effect", "glow effect"],
            # Animations
            8: ["text animation", "morphing text", "animated button", "hover animation"],
            # Backgrounds
            7: ["animated background", "gradient animation", "pattern animation"],
            # Interactive
            6: ["interactive component", "gesture animation", "scroll animation"]
        },
        "negative_patterns": []
    }
}

# Domain-specific keyword combinations that suggest multiple tools
DOMAIN_KEYWORDS = {
    "fullstack_dev": {
        "keywords": ["full stack", "fullstack", "frontend backend", "api and ui"],
        "suggested_tools": ["mcp__github__", "mcp__zen__", "mcp__filesystem__"]
    },
    "testing": {
        "keywords": ["test suite", "testing strategy", "qa automation", "test coverage"],
        "suggested_tools": ["mcp__zen__", "mcp__playwright__"]
    },
    "devops": {
        "keywords": ["ci/cd", "deployment", "infrastructure", "docker", "kubernetes"],
        "suggested_tools": ["mcp__github__", "mcp__zen__", "mcp__filesystem__"]
    },
    "debugging": {
        "keywords": ["debug error", "fix bug", "troubleshoot issue", "investigate problem"],
        "suggested_tools": ["mcp__zen__", "mcp__filesystem__", "mcp__tavily-remote__"]
    },
    "documentation": {
        "keywords": ["document code", "write docs", "api documentation", "readme"],
        "suggested_tools": ["mcp__zen__", "mcp__context7__", "mcp__filesystem__"]
    }
}

# Tool combination patterns with boosted confidence
TOOL_COMBINATIONS = {
    "github_workflow": {
        "patterns": [
            r"create.*pull request.*review",
            r"merge.*deploy.*github",
            r"github.*ci/cd.*pipeline"
        ],
        "tools": ["mcp__github__", "mcp__zen__"],
        "boost": 20
    },
    "python_debugging": {
        "patterns": [
            r"debug.*python.*error",
            r"python.*stack trace",
            r"fix.*python.*bug"
        ],
        "tools": ["mcp__filesystem__", "mcp__zen__"],
        "boost": 15
    },
    "web_testing": {
        "patterns": [
            r"test.*web.*application",
            r"browser.*test.*automation",
            r"e2e.*test.*suite"
        ],
        "tools": ["mcp__playwright__", "mcp__zen__"],
        "boost": 15
    },
    "architecture_planning": {
        "patterns": [
            r"design.*system.*architecture",
            r"plan.*infrastructure.*deployment",
            r"architect.*scalable.*solution"
        ],
        "tools": ["mcp__zen__", "mcp__filesystem__", "mcp__github__"],
        "boost": 25
    },
    "migration_project": {
        "patterns": [
            r"migrate.*database.*schema",
            r"upgrade.*framework.*version",
            r"refactor.*legacy.*code"
        ],
        "tools": ["mcp__zen__", "mcp__filesystem__"],
        "boost": 20
    }
}


class TriggerConfig:
    """Configuration manager for trigger keywords."""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent.parent / "keyword_triggers.json"
        self.log_path = Path(__file__).parent.parent.parent / "hook_logs" / "trigger_misses.json"
        self.mappings = self._load_config()
        self._ensure_log_dir()
    
    def _ensure_log_dir(self):
        """Ensure log directory exists."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file or use defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    custom_config = json.load(f)
                
                # Merge with defaults
                merged = DEFAULT_MCP_MAPPINGS.copy()
                for tool_id, config in custom_config.get("mcp_mappings", {}).items():
                    if tool_id in merged:
                        # Update existing tool
                        merged[tool_id]["keywords"].update(config.get("keywords", {}))
                        merged[tool_id]["priority"] = config.get("priority", merged[tool_id]["priority"])
                        if "negative_patterns" in config:
                            merged[tool_id]["negative_patterns"] = config["negative_patterns"]
                    else:
                        # Add new tool
                        merged[tool_id] = config
                
                return merged
            except Exception as e:
                print(f"Error loading config: {e}, using defaults")
        
        return DEFAULT_MCP_MAPPINGS.copy()
    
    def log_unmatched_prompt(self, prompt: str):
        """Log prompts that didn't match any tools for future refinement."""
        try:
            logs = []
            if self.log_path.exists():
                with open(self.log_path, 'r') as f:
                    logs = json.load(f)
            
            # Add new unmatched prompt
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "prompt": prompt,
                "words": list(set(prompt.lower().split()))
            })
            
            # Keep only last 100 entries
            logs = logs[-100:]
            
            with open(self.log_path, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception:
            # Silently fail on logging errors
            pass
    
    def save_example_config(self):
        """Save an example configuration file."""
        example = {
            "mcp_mappings": {
                "mcp__github__": {
                    "name": "GitHub MCP",
                    "priority": 8,
                    "keywords": {
                        "10": ["my-org github", "company repo"],
                        "8": ["deploy to prod", "release branch"]
                    },
                    "negative_patterns": ["test repo", "example github"]
                },
                "mcp__custom_tool__": {
                    "name": "Custom Tool",
                    "priority": 7,
                    "keywords": {
                        "9": ["custom keyword", "special term"],
                        "5": ["general term"]
                    }
                }
            },
            "domain_keywords": {
                "my_workflow": {
                    "keywords": ["specific workflow", "company process"],
                    "suggested_tools": ["mcp__github__", "mcp__custom_tool__"]
                }
            },
            "tool_combinations": {
                "custom_flow": {
                    "patterns": ["pattern.*to.*match"],
                    "tools": ["mcp__tool1__", "mcp__tool2__"],
                    "boost": 15
                }
            }
        }
        
        with open(self.config_path.with_suffix('.example.json'), 'w') as f:
            json.dump(example, f, indent=2)


def normalize_text(text: str) -> str:
    """Normalize text for keyword matching."""
    return " ".join(text.lower().split())


def check_negative_patterns(prompt: str, patterns: List[str]) -> bool:
    """Check if any negative patterns match the prompt.
    
    Returns True if a negative pattern is found (should exclude tool).
    """
    normalized_prompt = normalize_text(prompt)
    for pattern in patterns:
        if re.search(pattern, normalized_prompt, re.IGNORECASE):
            return True
    return False


def check_combination_patterns(prompt: str) -> List[Tuple[str, List[str], int]]:
    """Check for tool combination patterns.
    
    Returns list of (pattern_name, tools, boost) for matched patterns.
    """
    normalized_prompt = normalize_text(prompt)
    matches = []
    
    for name, config in TOOL_COMBINATIONS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, normalized_prompt, re.IGNORECASE):
                matches.append((name, config["tools"], config["boost"]))
                break
    
    return matches


def calculate_match_score(
    prompt: str, 
    tool_config: Dict, 
    matched_keywords: List[Tuple[str, int]],
    combination_boost: int = 0
) -> float:
    """Calculate a relevance score for tool matches.
    
    Returns a score between 0 and 100 based on:
    - Keyword priority (0-10)
    - Number of matches
    - Tool base priority
    - Combination pattern boosts
    """
    if not matched_keywords:
        return 0.0
    
    # Sum weighted scores
    keyword_score = sum(priority for _, priority in matched_keywords)
    
    # Bonus for multiple matches
    match_bonus = min(len(matched_keywords) * 2, 10)
    
    # Tool priority weight
    tool_priority = tool_config.get("priority", 5)
    
    # Calculate base score
    score = (keyword_score + match_bonus) * tool_priority
    
    # Add combination boost
    score += combination_boost
    
    return min(score, 100.0)


def find_matching_tools(prompt: str, config: TriggerConfig) -> List[Tuple[str, str, List[str], float]]:
    """Find MCP tools that match keywords in the prompt with scores.
    
    Returns:
        List of tuples: (tool_id, tool_name, matched_keywords, score)
    """
    normalized_prompt = normalize_text(prompt)
    matches = []
    
    # Check for combination patterns first
    combination_matches = check_combination_patterns(prompt)
    combination_boosts = {}
    for _, tools, boost in combination_matches:
        for tool in tools:
            combination_boosts[tool] = combination_boosts.get(tool, 0) + boost
    
    # Check standard tool keywords
    for tool_id, tool_config in config.mappings.items():
        # Check negative patterns first
        if check_negative_patterns(prompt, tool_config.get("negative_patterns", [])):
            continue
        
        matched_keywords = []
        
        for priority, keywords in tool_config.get("keywords", {}).items():
            # Convert string priority to int
            priority_int = int(priority) if isinstance(priority, str) else priority
            
            for keyword in keywords:
                pattern = r'\b' + re.escape(normalize_text(keyword)) + r'\b'
                if re.search(pattern, normalized_prompt):
                    matched_keywords.append((keyword, priority_int))
        
        if matched_keywords:
            boost = combination_boosts.get(tool_id, 0)
            score = calculate_match_score(normalized_prompt, tool_config, matched_keywords, boost)
            # Only include keywords, not priorities in the output
            keyword_list = [kw for kw, _ in matched_keywords]
            if boost > 0:
                keyword_list.append(f"combo-boost:{boost}")
            matches.append((tool_id, tool_config["name"], keyword_list, score))
    
    # Check domain-specific keywords
    for domain, domain_config in DOMAIN_KEYWORDS.items():
        for keyword in domain_config["keywords"]:
            pattern = r'\b' + re.escape(normalize_text(keyword)) + r'\b'
            if re.search(pattern, normalized_prompt):
                # Add suggested tools with medium score
                for tool_id in domain_config["suggested_tools"]:
                    if tool_id in config.mappings:
                        # Check if already in matches
                        existing = next((m for m in matches if m[0] == tool_id), None)
                        if not existing:
                            # Check negative patterns
                            if not check_negative_patterns(
                                prompt,
                                config.mappings[tool_id].get("negative_patterns", [])
                            ):
                                tool_name = config.mappings[tool_id]["name"]
                                boost = combination_boosts.get(tool_id, 0)
                                score = 50.0 + boost
                                keywords = [f"domain:{keyword}"]
                                if boost > 0:
                                    keywords.append(f"combo-boost:{boost}")
                                matches.append((tool_id, tool_name, keywords, score))
    
    # Sort by score (highest first)
    matches.sort(key=lambda x: x[3], reverse=True)
    
    return matches


def get_trigger_injection(user_prompt: Optional[str] = None) -> str:
    """Get MCP tool instructions based on keyword triggers with priority."""
    if not user_prompt:
        return ""
    
    config = TriggerConfig()
    
    # Find matching tools with scores
    matches = find_matching_tools(user_prompt, config)
    
    if not matches:
        # Log unmatched prompts for future analysis
        config.log_unmatched_prompt(user_prompt)
        return ""
    
    # Filter to only include high-scoring matches
    # Include top 3 or all with score > 30
    significant_matches = []
    for match in matches[:5]:  # Look at top 5
        if match[3] > 30 or len(significant_matches) < 3:
            significant_matches.append(match)
    
    if not significant_matches:
        return ""
    
    # Build injection instructions
    instructions = []
    
    for tool_id, tool_name, keywords, score in significant_matches:
        # Format keywords
        display_keywords = [kw for kw in keywords if not kw.startswith("combo-boost:")]
        keywords_str = ", ".join(f'"{kw}"' for kw in display_keywords[:3])
        if len(display_keywords) > 3:
            keywords_str += f" (+{len(display_keywords) - 3} more)"
        
        # Check if combination boost was applied
        combo_boost = any(kw.startswith("combo-boost:") for kw in keywords)
        
        # Stronger language for higher scores
        if score > 70:
            prefix = "🔴 CRITICAL"
            suffix = "This tool is HIGHLY RECOMMENDED for optimal results!"
            if combo_boost:
                suffix += " (Pattern match bonus applied)"
        elif score > 50:
            prefix = "🟡 IMPORTANT"
            suffix = "Consider using this tool for better results."
            if combo_boost:
                suffix += " (Pattern match bonus)"
        else:
            prefix = "🟢 SUGGESTED"
            suffix = "This tool may be helpful."
        
        instruction = (
            f"{prefix}: Keywords detected ({keywords_str}) [score: {score:.0f}] - "
            f"Use {tool_id} ({tool_name}). {suffix}"
        )
        instructions.append(instruction)
    
    # Combine all instructions
    combined = "\n".join(instructions)
    return (
        f"\n<mcp-tool-triggers>\n"
        f"⚡ MCP TOOL RECOMMENDATIONS (Priority Ranked) ⚡\n"
        f"{combined}\n"
        f"</mcp-tool-triggers>"
    )


# Create example config on module load
if __name__ == "__main__":
    config = TriggerConfig()
    config.save_example_config()
    
    # Test with various prompts
    test_prompts = [
        "Can you help me create a pull request on github?",
        "I need to analyze this complex architecture and debug the issue",
        "Find all references to the User class in my python code",
        "Set up a CI/CD pipeline with github actions",
        "Create a full stack application with React and Django",
        "Debug this error in my test suite",
        "This is not an issue, just a comment",
        "Migrate the database schema to the new version",
        "Design a scalable system architecture for deployment"
    ]
    
    print("Testing trigger injection with enhancements...\n")
    
    for prompt in test_prompts:
        print(f"Prompt: {prompt}")
        injection = get_trigger_injection(prompt)
        if injection:
            print(injection)
        else:
            print("No triggers matched (logged for analysis)")
        print("-" * 70)
        print()