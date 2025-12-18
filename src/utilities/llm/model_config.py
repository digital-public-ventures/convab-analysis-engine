"""LLM model configuration profiles and rate limits."""


class ModelProfile:
    """Model configuration profile with rate limits and capabilities."""

    def __init__(self, model_id: str, rpm: int, tpm: int, rpd: int, allowed_thinking: list[str]):
        """Initialize a model profile.

        Args:
            model_id: Full model identifier
            rpm: Requests per minute limit
            tpm: Tokens per minute limit
            rpd: Requests per day limit
            allowed_thinking: List of allowed thinking levels
        """
        self.model_id = model_id
        self.rpm = rpm
        self.tpm = tpm
        self.rpd = rpd
        self.allowed_thinking = allowed_thinking


# TODO: Expand MODELS to support multiple providers similar to costs.py structure:
# MODELS = {
#     'gemini': {
#         'flash': ModelProfile(...),
#         'pro': ModelProfile(...),
#     },
#     'openai': {
#         'gpt-5.2': ModelProfile(...),
#         'gpt-5-mini': ModelProfile(...),
#     },
#     'anthropic': {
#         'claude-sonnet-4.5': ModelProfile(...),
#     },
# }
# This would enable unified model selection across providers while maintaining
# provider-specific rate limits and capabilities.

# Current single-provider structure (Gemini only)
MODELS = {
    'flash': ModelProfile(
        model_id='gemini-3-flash-preview',
        rpm=1000,
        tpm=1_000_000,
        rpd=10_000,
        allowed_thinking=['MINIMAL', 'LOW', 'MEDIUM', 'HIGH'],
    ),
    'pro': ModelProfile(
        model_id='gemini-3-pro-preview',
        rpm=25,
        tpm=1_000_000,
        rpd=250,
        allowed_thinking=['LOW', 'MEDIUM', 'HIGH'],  # Pro does NOT support MINIMAL
    ),
}
