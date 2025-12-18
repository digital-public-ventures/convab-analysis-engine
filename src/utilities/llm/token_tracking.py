"""Token usage tracking utilities."""

import json
from datetime import datetime
from pathlib import Path

from ..llm.costs import calculate_cost


def record_token_usage(
    total_tokens: int,
    model: str,
    input_tokens: int = 0,
    thinking_tokens: int = 0,
    output_tokens: int = 0,
    token_usage_file: str = 'temp/token_usage.jsonl',
) -> None:
    """Record token usage to a JSONL file with cost calculation.

    Args:
        total_tokens: Total number of tokens used
        model: Model identifier
        input_tokens: Number of input tokens (default: 0)
        thinking_tokens: Number of thinking tokens (default: 0)
        output_tokens: Number of output tokens (default: 0)
        token_usage_file: Path to the JSONL file (default: temp/token_usage.jsonl)
    """
    usage_file = Path(token_usage_file)
    usage_file.parent.mkdir(parents=True, exist_ok=True)

    # Calculate cost
    total_cost = calculate_cost(input_tokens, output_tokens, thinking_tokens, model)

    record = {
        'timestamp': datetime.now().isoformat(),
        'total_tokens': total_tokens,
        'input_tokens': input_tokens,
        'thinking_tokens': thinking_tokens,
        'output_tokens': output_tokens,
        'model': model,
        'total_cost': total_cost,
    }

    with open(usage_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')
