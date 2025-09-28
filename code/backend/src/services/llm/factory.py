"""
LLM Service Factory
"""
import logging
from typing import Dict, Any, Optional

from ...config import settings
from .base import BaseLLMService, LLMConfig
from .openrouter_service import OpenRouterLLMService

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM services"""

    _services = {
        "openrouter": OpenRouterLLMService,
        "deepseek": OpenRouterLLMService,  # Alias for OpenRouter with DeepSeek
    }

    @classmethod
    def create_service(
        cls,
        service_type: str = "openrouter",
        model: Optional[str] = None,
        **kwargs
    ) -> BaseLLMService:
        """Create LLM service instance"""
        if service_type not in cls._services:
            available = list(cls._services.keys())
            raise ValueError(f"Unknown service type: {service_type}. Available: {available}")

        # Default configuration
        config = LLMConfig(
            model=model or settings.deepseek_model,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 1000),
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=kwargs.get("timeout", 60)
        )

        service_class = cls._services[service_type]
        return service_class(config)

    @classmethod
    def get_available_services(cls) -> Dict[str, str]:
        """Get available service types"""
        return {
            name: service_class.__name__
            for name, service_class in cls._services.items()
        }

    @classmethod
    def create_from_config(cls, config_dict: Dict[str, Any]) -> BaseLLMService:
        """Create service from configuration dictionary"""
        service_type = config_dict.get("type", "openrouter")
        model = config_dict.get("model", settings.deepseek_model)

        # Extract LLM-specific config
        llm_config = {
            k: v for k, v in config_dict.items()
            if k not in ["type", "model"]
        }

        return cls.create_service(
            service_type=service_type,
            model=model,
            **llm_config
        )

    @classmethod
    async def test_service(cls, service_type: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Test LLM service connectivity"""
        try:
            service = cls.create_service(service_type, model)
            async with service:
                health = await service.check_health()
                models = await service.get_available_models()

                return {
                    "service_type": service_type,
                    "healthy": health.get("healthy", False),
                    "model": model,
                    "available_models_count": len(models),
                    "test_timestamp": "now"
                }

        except Exception as e:
            logger.error(f"Service test failed for {service_type}: {e}")
            return {
                "service_type": service_type,
                "healthy": False,
                "error": str(e),
                "test_timestamp": "now"
            }

    @classmethod
    def register_service(cls, name: str, service_class: type):
        """Register a new LLM service"""
        if not issubclass(service_class, BaseLLMService):
            raise TypeError("Service class must inherit from BaseLLMService")

        cls._services[name] = service_class
        logger.info(f"Registered LLM service: {name}")

    @classmethod
    def unregister_service(cls, name: str):
        """Unregister an LLM service"""
        if name in cls._services:
            del cls._services[name]
            logger.info(f"Unregistered LLM service: {name}")
        else:
            logger.warning(f"Service {name} not found for unregistration")