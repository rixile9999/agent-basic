from openai import OpenAI
import os, sys
from pathlib import Path

prompt_file = sys.argv[1]
custom_prompt = Path(prompt_file).read_text(encoding='utf-8')
user_text = sys.stdin.read()
client = OpenAI(
    # API keys differ by region. If you haven't configured an environment variable, replace the next line with: api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # If you use Beijing region models, replace base_url with: https://dashscope.aliyuncs.com/compatible-mode/v1
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

completion = client.chat.completions.create(
    model="qwen3.6-plus",
    messages=[
        {
            "role": "system",
            "content": custom_prompt
        },
        {
            "role": "user",
            "content": user_text,
        },
    ],
    response_format={"type": "json_object"},
    stream=True,
    stream_options={"include_usage": True}
)

content_parts = []

for chunk in completion:
    if chunk.choices:
        content = chunk.choices[0].delta.content or ""
        print(content, end="", flush=True)
        content_parts.append(content)
    elif chunk.usage:
        print("\n--- Request Usage ---")
        print(f"Input Tokens: {chunk.usage.prompt_tokens}")
        print(f"Output Tokens: {chunk.usage.completion_tokens}")
        print(f"Total Tokens: {chunk.usage.total_tokens}")

full_response = "".join(content_parts)
