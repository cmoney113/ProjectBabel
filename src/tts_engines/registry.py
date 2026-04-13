"""
TTS Engine Registry
Dynamic registration and lookup of TTS engines
"""

import logging
from typing import Dict, Type, Optional, Any, Callable
from pathlib import Path

from .base import TTSEngine

logger = logging.getLogger(__name__)


class TTSEngineRegistry:
    """
    Registry for TTS engines with lazy loading support.

    Usage:
        registry = TTSEngineRegistry()

        # Register an engine class (lazy)
        registry.register("kittentts", KittenTTSEngine,
                         model_path="/path/to/model.onnx")

        # Get an engine instance (creates on first access)
        engine = registry.get("kittentts")

        # Synthesize
        audio = engine.synthesize("Hello world", voice="Jasper")
    """

    def __init__(self):
        self._engine_classes: Dict[str, Type[TTSEngine]] = {}
        self._engine_instances: Dict[str, TTSEngine] = {}
        self._engine_configs: Dict[str, Dict[str, Any]] = {}
        self._factories: Dict[str, Callable[[], TTSEngine]] = {}

    def register(
        self,
        model_id: str,
        engine_class: Type[TTSEngine] = None,
        factory: Callable[[], TTSEngine] = None,
        **config
    ) -> None:
        """
        Register a TTS engine.

        Args:
            model_id: Unique model identifier (e.g., "kittentts")
            engine_class: Engine class to instantiate
            factory: Factory function that creates the engine (alternative to engine_class)
            **config: Configuration parameters passed to engine constructor
        """
        if factory:
            self._factories[model_id] = factory
        elif engine_class:
            self._engine_classes[model_id] = engine_class
            self._engine_configs[model_id] = config
        else:
            raise ValueError("Must provide either engine_class or factory")

        logger.debug(f"Registered TTS engine: {model_id}")

    def get(self, model_id: str) -> Optional[TTSEngine]:
        """
        Get an engine instance by model ID.
        Creates the instance on first access (lazy loading).

        Args:
            model_id: Model identifier

        Returns:
            TTSEngine instance or None if not registered
        """
        # Check if already instantiated
        if model_id in self._engine_instances:
            return self._engine_instances[model_id]

        # Create from factory
        if model_id in self._factories:
            try:
                engine = self._factories[model_id]()
                self._engine_instances[model_id] = engine
                logger.info(f"Created TTS engine via factory: {model_id}")
                return engine
            except Exception as e:
                logger.error(f"Failed to create engine via factory: {e}")
                return None

        # Create from class + config
        if model_id in self._engine_classes:
            engine_class = self._engine_classes[model_id]
            config = self._engine_configs.get(model_id, {})
            try:
                engine = engine_class(**config)
                self._engine_instances[model_id] = engine
                logger.info(f"Created TTS engine: {model_id}")
                return engine
            except Exception as e:
                logger.error(f"Failed to create engine {model_id}: {e}")
                return None

        logger.warning(f"Engine not registered: {model_id}")
        return None

    def is_registered(self, model_id: str) -> bool:
        """Check if a model is registered"""
        return (
            model_id in self._engine_classes or
            model_id in self._factories or
            model_id in self._engine_instances
        )

    def is_loaded(self, model_id: str) -> bool:
        """Check if a model is loaded"""
        if model_id in self._engine_instances:
            return self._engine_instances[model_id].is_loaded()
        return False

    def unload(self, model_id: str) -> bool:
        """Unload an engine to free memory"""
        if model_id in self._engine_instances:
            engine = self._engine_instances[model_id]
            success = engine.unload()
            if success:
                del self._engine_instances[model_id]
                logger.info(f"Unloaded TTS engine: {model_id}")
            return success
        return True  # Not loaded, consider success

    def list_engines(self) -> list:
        """List all registered engine IDs"""
        return list(set(
            list(self._engine_classes.keys()) +
            list(self._factories.keys()) +
            list(self._engine_instances.keys())
        ))

    def clear(self) -> None:
        """Clear all registered engines"""
        self._engine_classes.clear()
        self._engine_instances.clear()
        self._engine_configs.clear()
        self._factories.clear()


# Global registry instance
_registry: Optional[TTSEngineRegistry] = None


def get_registry() -> TTSEngineRegistry:
    """Get the global TTS engine registry"""
    global _registry
    if _registry is None:
        _registry = TTSEngineRegistry()
    return _registry


def register_builtin_engines(models_dir: str = None) -> None:
    """
    Register all built-in TTS engines.

    Args:
        models_dir: Base models directory (defaults to project models/)
    """
    if models_dir is None:
        models_dir = Path(__file__).parent.parent.parent / "models"
    models_dir = Path(models_dir)

    registry = get_registry()

    # KittenTTS
    def create_kittentts():
        from .kittentts_engine import KittenTTSEngine
        return KittenTTSEngine(
            model_path=str(models_dir / "kittentts" / "kitten_tts_mini_v0_8.onnx"),
            voices_path=str(models_dir / "kittentts" / "voices.npz"),
        )

    registry.register("kittentts", factory=create_kittentts)

    # VibeVoice
    def create_vibevoice():
        from .vibevoice_engine import VibeVoiceEngine
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        engine = VibeVoiceEngine(
            model_path=str(models_dir / "VibeVoiceRealtime05b"),
            device=device,
        )
        engine.load()
        return engine

    registry.register("vibevoice", factory=create_vibevoice)

    logger.info("Registered built-in TTS engines")
