"""
Prompts for DataPilot agents.

This module loads prompts from prompts.yaml and exposes them as constants
for backward compatibility with existing imports.

Prompts are stored in src/prompts.yaml for easier editing and version control.
"""
import yaml
from pathlib import Path
from typing import Dict, Any

# Load prompts from YAML file
_PROMPTS_FILE = Path(__file__).parent / "prompts.yaml"
_PROMPTS_CACHE: Dict[str, Any] = None


def _load_prompts() -> Dict[str, Any]:
    """Load prompts from YAML file (cached)."""
    global _PROMPTS_CACHE
    if _PROMPTS_CACHE is None:
        if not _PROMPTS_FILE.exists():
            raise FileNotFoundError(
                f"Prompts file not found: {_PROMPTS_FILE}. "
                "Please ensure prompts.yaml exists in the src/ directory."
            )
        with open(_PROMPTS_FILE, 'r', encoding='utf-8') as f:
            _PROMPTS_CACHE = yaml.safe_load(f)
    return _PROMPTS_CACHE


def _get_prompt(section: str, key: str) -> str:
    """Get a prompt from the YAML structure."""
    prompts = _load_prompts()
    return prompts[section][key].strip()


# ============================================================================
# Intent Clarifier Prompts
# ============================================================================

INTENT_CLARIFIER_SYSTEM_PROMPT = _get_prompt("intent_clarifier", "system_prompt")
INTENT_CLARIFIER_CLARIFICATION_SYSTEM_PROMPT = _get_prompt("intent_clarifier", "clarification_system_prompt")
INTENT_CLARIFIER_CLARIFICATION_USER_PROMPT = _get_prompt("intent_clarifier", "clarification_user_prompt")


# ============================================================================
# SQL Generator Prompts
# ============================================================================

SQL_GENERATOR_SYSTEM_PROMPT = _get_prompt("sql_generator", "system_prompt")
SQL_GENERATOR_USER_PROMPT_TEMPLATE = _get_prompt("sql_generator", "user_prompt_template")


# ============================================================================
# Insight Generator Prompts
# ============================================================================

INSIGHT_GENERATOR_SYSTEM_PROMPT = _get_prompt("insight_generator", "system_prompt")
INSIGHT_GENERATOR_USER_PROMPT_TEMPLATE = _get_prompt("insight_generator", "user_prompt_template")


# ============================================================================
# ReAct Agent Prompt (for future use with LangChain agents)
# ============================================================================

REACT_PROMPT_WITH_FORMAT_INSTRUCTIONS = _get_prompt("react_agent", "prompt_with_format_instructions")

