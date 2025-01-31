from llama_index.core.llms import CustomLLM, CompletionResponse, LLMMetadata
from openai import OpenAI, APIError
from typing import Optional, List, Any
from pydantic import PrivateAttr
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekLLM(CustomLLM):
    # Required Pydantic fields
    model_name: str = "deepseek-reasoner"  # Declare this explicitly
    
    # Private attributes
    _client: OpenAI = PrivateAttr()
    _is_reasoner: bool = PrivateAttr()

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-reasoner"):
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable or api_key parameter required")
        super().__init__()
        self._client = OpenAI(
            api_key=api_key.strip(),
            base_url="https://api.deepseek.com/v1",
            timeout=30,
            max_retries=3
        )
        self.model_name = model  # Assign to the declared field
        self._is_reasoner = "reasoner" in model.lower()
        logger.info(f"Initialized with model: {self.model_name}")

    def complete(self, prompt: str, **kwargs) -> CompletionResponse:
        try:
            params = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 1024)
            }
            if not self._is_reasoner:
                params["temperature"] = kwargs.get("temperature", 0.7)
                
            response = self._client.chat.completions.create(**params)
            return CompletionResponse(text=response.choices[0].message.content)
            
        except APIError as e:
            logger.error(f"API Error: {e}")
            return CompletionResponse(text=f"Error: {str(e)}")

    def stream_complete(self, prompt: str, **kwargs: Any):
        raise NotImplementedError("Streaming not supported")

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=128000,
            model_name=self.model_name,
            is_chat_model=True
        )

# Test with your key
llm = DeepSeekLLM(api_key="sk-7cb9d35fa9e34ce18d1c4aff62c3f628")
response = llm.complete("Write 'Hello World' in Python")
print(response.text)
