"""
Ollama LLM Integration Module
Handles conversation logic with local LLM models
"""
import json
import logging
from typing import List, Dict, Optional
import requests

logger = logging.getLogger(__name__)


class OllamaLLM:
    """Ollama-based LLM for conversational AI"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "mistral",
        timeout: Optional[tuple] = None
    ):
        """
        Initialize Ollama LLM
        
        Args:
            base_url: Ollama API base URL
            model: Model name to use (must be pulled via ollama pull)
            timeout: (connect, read) timeout tuple for HTTP calls
        """
        self.base_url = base_url
        self.model = model
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = ""
        # Allow plenty of time for local models to stream the first token
        self.timeout = timeout or (10, 180)
        
    def set_system_prompt(self, prompt: str):
        """Set the system prompt for the agent personality"""
        self.system_prompt = prompt
        logger.info(f"System prompt set: {prompt[:50]}...")
    
    def load_personality(self, config: Dict):
        """
        Load agent personality from config
        
        Args:
            config: Agent configuration dictionary
        """
        template = config.get("system_prompt_template", 
                             "You are a {agent_role}. {agent_description}. Your tone should be {tone}.\n\nIMPORTANT: Keep your responses SHORT and CONCISE. Aim for 1-2 sentences maximum (under 100 words). Be direct and clear.")
        
        system_prompt = template.format(
            agent_role=config.get("agent_role", "Assistant"),
            agent_description=config.get("agent_description", ""),
            tone=config.get("tone", "friendly")
        )
        
        self.set_system_prompt(system_prompt)
        logger.info(f"Loaded personality: {config.get('agent_role', 'Assistant')}")
    
    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({"role": role, "content": content})
        # Keep last 10 exchanges to avoid context overflow
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def generate_response(self, user_message: str, stream: bool = False) -> str:
        """
        Generate LLM response
        
        Args:
            user_message: User's input message
            stream: Whether to stream the response (not implemented yet)
            
        Returns:
            str: LLM response
        """
        # Add user message to history
        self.add_to_history("user", user_message)
        
        # Prepare messages for Ollama
        messages = []
        
        # Add system prompt if available
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        # Prepare request
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }
        
        try:
            logger.info(f"Sending request to Ollama: {self.model}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            assistant_message = result.get("message", {}).get("content", "")
            
            # Add assistant response to history
            self.add_to_history("assistant", assistant_message)
            
            logger.info(f"Received response: {assistant_message[:50]}...")
            return assistant_message
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API: {e}")
            return "I'm sorry, I'm having trouble processing your request right now. Please try again."
    
    def generate_response_stream(self, user_message: str):
        """
        Generate LLM response with streaming
        
        Args:
            user_message: User's input message
            
        Yields:
            str: Chunks of the response
        """
        # Add user message to history
        self.add_to_history("user", user_message)
        
        # Prepare messages
        messages = []
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        messages.extend(self.conversation_history)
        
        # Prepare request
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_predict": 150  # Limit response to ~150 tokens (roughly 100-120 words)
            }
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            full_response += content
                            yield content
                    except json.JSONDecodeError:
                        continue
            
            # Add complete response to history
            self.add_to_history("assistant", full_response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API: {e}")
            yield "I'm sorry, I'm having trouble processing your request right now."

