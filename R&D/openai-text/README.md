# OpenAI Text Chat Service

Simple Python service for OpenAI chat conversations.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your-api-key-here
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini  # Optional, defaults to gpt-4o-mini
```

## Usage

### As a CLI tool:
```bash
python chat_service.py "Hello, how are you?"
```

### As a Python module:
```python
from chat_service import OpenAIChatService

service = OpenAIChatService()
response = service.chat([
    {"role": "user", "content": "Hello!"}
])
print(response["content"])
```

### Streaming:
```python
from chat_service import OpenAIChatService

service = OpenAIChatService()
for chunk in service.chat_stream([
    {"role": "user", "content": "Tell me a story"}
]):
    print(chunk, end="", flush=True)
```



