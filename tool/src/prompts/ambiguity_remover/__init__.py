"""
Domain-specific system prompts for the AmbiguityRemover agent.

Each module (factual, activity, procedural) provides get_system_prompt() function
that generates a clarification-focused system prompt tailored to its domain.

The prompts prioritize:
1. Simplicity - avoiding legal jargon
2. Necessity - only asking when truly needed
3. Specificity - being concrete about what information is missing
4. User-friendliness - explaining WHY clarification matters in plain English
"""
