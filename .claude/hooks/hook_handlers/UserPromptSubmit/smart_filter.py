"""Smart filter using NLP for intelligent Zen consultation decisions."""

import hashlib
import re
from functools import lru_cache
from typing import Any, Dict, Tuple

# Try to import spacy, fallback to regex if not available
try:
    import spacy

    NLP_AVAILABLE = True
    # Load the small English model for speed
    try:
        nlp = spacy.load("en_core_web_sm", disable=["ner", "textcat", "lemmatizer"])
    except (OSError, IOError, ValueError):
        # Model not found, file access issues, or configuration problems
        NLP_AVAILABLE = False
except ImportError:
    NLP_AVAILABLE = False


class SmartZenFilter:
    """Intelligent filter that analyzes prompt complexity and intent."""

    def __init__(self):
        # Intent patterns with complexity weights (made more lenient)
        self.intent_patterns = {
            # High complexity (0.8-1.0)
            "architecture": (r"\b(architect|design|pattern|structure|system)\b", 0.9),
            "debugging": (r"\b(debug|troubleshoot|fix|issue|problem|error)\b", 0.8),
            "optimization": (r"\b(optimiz|performance|efficient|scale|improve)\b", 0.8),
            "analysis": (r"\b(analyz|understand|explain|evaluate|assess)\b", 0.8),  # Increased from 0.7
            "decision": (r"\b(should|choose|decide|compare|versus|vs)\b", 0.8),  # Increased from 0.7
            "implementation": (
                r"\b(implement|build|create|develop|add feature)\b",
                0.8,
            ),
            # Medium complexity (0.4-0.7) - made more generous
            "modification": (r"\b(refactor|change|modify|update|enhance)\b", 0.7),  # Increased from 0.6
            "question": (r"\b(how|why|what|when|where|could|would)\b", 0.6),  # Increased from 0.5
            "planning": (r"\b(plan|strategy|approach|method|way)\b", 0.7),  # Increased from 0.6
            "collaboration": (r"\b(help|assist|guide|work together|brainstorm)\b", 0.6),  # New pattern
            # Low complexity (0.0-0.4) - made more generous
            "simple_action": (
                r"\b(read|write|delete|rename|move|copy|show|list)\b",
                0.3,  # Increased from 0.2
            ),
            "status": (r"\b(status|version|help|info|check)\b", 0.2),  # Increased from 0.1
            "format": (r"\b(format|indent|style|clean)\b", 0.3),  # Increased from 0.2
        }

        # Complexity modifiers (enhanced and more generous)
        self.complexity_modifiers = {
            "multiple_files": (r"\b(files|multiple|all|entire|whole)\b", 0.3),  # Increased from 0.2
            "conditional": (r"\b(if|when|unless|except|but)\b", 0.2),  # Increased from 0.1
            "comparison": (r"\b(better|worse|versus|vs|compare|than)\b", 0.3),  # Increased from 0.2
            "uncertainty": (r"\b(might|maybe|perhaps|possibly|could be)\b", 0.2),  # Increased from 0.1
            "code_references": (r"\b(function|class|method|variable|import|export)\b", 0.2),  # New
            "technical_terms": (r"\b(api|database|server|client|configuration|deployment)\b", 0.2),  # New
            "time_pressure": (r"\b(urgent|quickly|asap|immediately|now)\b", 0.2),  # New
            "scope_words": (r"\b(project|codebase|system|application|feature)\b", 0.1),  # New
        }

    def _pattern_analysis(self, text: str) -> Tuple[float, str]:
        """Fallback pattern-based analysis."""
        text_lower = text.lower()
        score = 0.0
        matched_intents = []

        # Check intent patterns
        for intent_name, (pattern, weight) in self.intent_patterns.items():
            if re.search(pattern, text_lower):
                score += weight
                matched_intents.append(intent_name)

        # Apply modifiers
        for modifier_name, (pattern, modifier) in self.complexity_modifiers.items():
            if re.search(pattern, text_lower):
                score += modifier
                matched_intents.append(f"+{modifier_name}")

        # Length-based adjustment (enhanced)
        word_count = len(text.split())
        if word_count > 15:  # Lowered threshold from 20
            score += 0.2  # Increased from 0.1
            matched_intents.append("detailed_request")
        elif word_count > 8:  # Additional tier for medium-length prompts
            score += 0.1
            matched_intents.append("medium_length")

        # Normalize score
        score = min(score, 1.0)

        reasoning = f"pattern_match: {', '.join(matched_intents) if matched_intents else 'none'}"
        return score, reasoning

    def _nlp_analysis(self, text: str) -> Tuple[float, str]:
        """Analyze using spaCy for deeper understanding."""
        doc = nlp(text)
        score = 0.0
        factors = []

        # Analyze sentence complexity
        for sent in doc.sents:
            # Count dependencies indicating complexity
            complex_deps = ["advcl", "ccomp", "xcomp", "acl", "relcl"]
            complexity_count = sum(1 for token in sent if token.dep_ in complex_deps)

            if complexity_count > 0:
                score += 0.2
                factors.append("complex_sentence_structure")

            # Check for questions requiring analysis
            if sent.text.strip().endswith("?"):
                # Analyze question type
                root = (
                    [token for token in sent if token.dep_ == "ROOT"][0]
                    if sent
                    else None
                )
                if root and root.lemma_ in ["be", "should", "could", "would"]:
                    score += 0.3
                    factors.append("analytical_question")

        # Check for technical/domain terms
        noun_phrases = [chunk.text for chunk in doc.noun_chunks]
        if any(len(np) > 2 for np in noun_phrases):
            score += 0.2
            factors.append("technical_concepts")

        # Entity and concept density
        content_tokens = [t for t in doc if t.pos_ in ["NOUN", "VERB", "ADJ"]]
        if len(content_tokens) / len(doc) > 0.4:
            score += 0.1
            factors.append("high_content_density")

        # Apply pattern analysis on top
        pattern_score, pattern_factors = self._pattern_analysis(text)
        score = (score + pattern_score) / 2
        factors.extend(pattern_factors)

        reasoning = f"nlp_analysis: {', '.join(set(factors))}"
        return min(score, 1.0), reasoning

    @lru_cache(maxsize=256)
    def analyze_complexity(self, text: str) -> Tuple[bool, float, str]:
        """Analyze prompt complexity using NLP or pattern matching.

        Returns:
            Tuple of (should_use_zen, confidence_score, reasoning)
        """
        # Quick checks
        if len(text) < 15:
            return False, 0.1, "too_short"

        # Use NLP if available
        if NLP_AVAILABLE:
            score, reasoning = self._nlp_analysis(text)
        else:
            score, reasoning = self._pattern_analysis(text)

        # Decision threshold (lowered to be more inclusive)
        should_use = score >= 0.3  # Reduced from 0.5 to trigger more often

        return should_use, score, reasoning

    def get_cache_key(self, text: str) -> str:
        """Generate a cache key for the prompt."""
        return hashlib.md5(text.encode()).hexdigest()[:16]


# Global instance
_filter_instance = None


def get_smart_filter() -> SmartZenFilter:
    """Get or create the global filter instance."""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = SmartZenFilter()
    return _filter_instance


def should_use_zen_smart(prompt: str) -> Tuple[bool, Dict[str, Any]]:
    """Smart decision on whether to use Zen consultation.

    Returns:
        Tuple of (should_use, metadata_dict)
    """
    filter_instance = get_smart_filter()
    should_use, score, reasoning = filter_instance.analyze_complexity(prompt)

    return should_use, {
        "score": score,
        "reasoning": reasoning,
        "cache_key": filter_instance.get_cache_key(prompt),
    }
