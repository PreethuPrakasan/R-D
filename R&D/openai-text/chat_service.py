"""
Simple OpenAI chat service for text conversations.
This service can be used as a standalone script or imported as a module.
"""

import os
import sys
import json
from typing import Optional, List, Dict, Any
from openai import OpenAI


class OpenAIChatService:
    """Service for handling OpenAI chat conversations."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI chat service.
        
        Args:
            api_key: OpenAI API key. If not provided, will try to get from OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send a chat message to OpenAI and get a response.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
                     Example: [{"role": "user", "content": "Hello"}]
            model: Model to use (defaults to self.model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            
        Returns:
            Dictionary with 'content' (response text) and 'usage' (token usage info)
        """
        try:
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason,
            }
        except Exception as e:
            return {
                "error": str(e),
                "content": None,
            }
    
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """
        Stream chat responses from OpenAI.
        
        Args:
            messages: List of message dictionaries
            model: Model to use
            temperature: Sampling temperature
            
        Yields:
            Chunks of the response as they arrive
        """
        try:
            stream = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"Error: {str(e)}"


def main():
    """CLI interface for testing the chat service."""
    if len(sys.argv) < 2:
        print("Usage: python chat_service.py <message>")
        print("Or set OPENAI_API_KEY environment variable and use as module")
        sys.exit(1)
    
    message = sys.argv[1]
    
    try:
        service = OpenAIChatService()
        response = service.chat([
            {"role": "user", "content": message}
        ])
        
        if "error" in response:
            print(f"Error: {response['error']}", file=sys.stderr)
            sys.exit(1)
        
        print(response["content"])
        if "usage" in response:
            print(f"\n[Tokens used: {response['usage']['total_tokens']}]", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()



