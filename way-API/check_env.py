#!/usr/bin/env python3
"""
Check environment variables
"""
import os
from dotenv import load_dotenv

print("🔍 Environment Variables Check")
print("=" * 40)

# Load .env file
load_dotenv()

# Check the auth variables
basic_user = os.getenv("BASIC_AUTH_USERNAME", "admin")
basic_pass = os.getenv("BASIC_AUTH_PASSWORD", "secret")

print(f"BASIC_AUTH_USERNAME: '{basic_user}'")
print(f"BASIC_AUTH_PASSWORD: '{basic_pass}'")

# Check OpenAI variables
openai_key = os.getenv("OPENAI_API_KEY", "NOT_SET")
openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

print(f"OPENAI_API_KEY: {'*' * 20}{openai_key[-4:] if len(openai_key) > 4 else 'NOT_SET'}")
print(f"OPENAI_MODEL: '{openai_model}'")

print("\n💡 To fix authentication, make sure your .env file contains:")
print(f"BASIC_AUTH_USERNAME={basic_user}")
print(f"BASIC_AUTH_PASSWORD={basic_pass}")
