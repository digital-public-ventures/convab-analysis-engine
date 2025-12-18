import argparse
import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

# 1. SETUP: Explicit Credentials
# Replace with your actual key if not using environment variables
API_KEY = os.environ.get('GEMINI_API_KEY', 'YOU_FORGOT_TO_SET_GEMINI_API_KEY')

# Initialize the Official SDK Client
client = genai.Client(api_key=API_KEY)


def generate_with_gemini(
    prompt: str,
    model_id: str = 'gemini-3-flash-preview',
    thinking_level: str = 'LOW',
    system_prompt: str | None = None,
) -> None:
    """Uses the Official SDK to send a complex reasoning request.

    Args:
        prompt: The user prompt (required)
        model_id: The Gemini model to use (default: gemini-3-flash-preview)
        thinking_level: Thinking level - LOW, MEDIUM, or HIGH (default: HIGH)
        system_prompt: Optional system instruction to guide model behavior
    """
    print(f'--- Sending Request to {model_id} ---')

    # Configure Gemini Thinking
    # thinking_level options: "LOW", "MEDIUM", "HIGH" (for Gemini 3)
    # or "MINIMAL" (for Gemini 3 Flash only)
    thinking_level_enum = types.ThinkingLevel[thinking_level.upper()]
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level_enum, include_thoughts=True)
    )

    # Add system instruction if provided
    if system_prompt:
        config.system_instruction = system_prompt

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=config,
        )

        # Parse the response to separate 'Thoughts' from the 'Answer'
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.thought and part.text:
                    print(f'\n[Thinking Process ({len(part.text)} chars)]:')
                    print(f'{part.text[:200]}... (truncated for brevity)')
                elif part.text:
                    print(f'\n[Final Answer]:\n{part.text}')
        else:
            print('\n[No response generated]')

        # Show Token Usage (Cost of this specific request)
        if response.usage_metadata:
            print(f'\n[Cost]: {response.usage_metadata.total_token_count} tokens used.')

    except errors.APIError as e:
        print(f'API Error: {e}')
    except (KeyError, ValueError) as e:
        print(f'Configuration Error: {e}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate content using Gemini API with thinking capabilities')
    parser.add_argument('prompt', type=str, help='User prompt (required)')
    parser.add_argument(
        '--model', type=str, default='gemini-3-flash-preview', help='Model ID (default: gemini-3-flash-preview)'
    )
    parser.add_argument(
        '--thinking-level',
        type=str,
        default='HIGH',
        choices=['MINIMAL', 'LOW', 'MEDIUM', 'HIGH'],
        help='Thinking level (default: HIGH)',
    )
    parser.add_argument(
        '--system-prompt', type=str, default=None, help='Optional system instruction to guide model behavior'
    )

    args = parser.parse_args()

    generate_with_gemini(
        prompt=args.prompt,
        model_id=args.model,
        thinking_level=args.thinking_level,
        system_prompt=args.system_prompt,
    )
