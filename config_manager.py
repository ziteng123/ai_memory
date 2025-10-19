"""
Configuration Manager for Memory MCP Server

Handles loading and validation of server configuration including
Redis connection settings and mem0 configuration.
"""

import json
import os
from typing import Any, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration for the Memory MCP Server."""
    
    DEFAULT_CONFIG = {
        "redis": {
            "url": "redis://localhost:6379",
            "collection_name": "mcp_memories",
            "db": 0
        },
        "mem0": {
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": "llama3.2:3b",
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
            },
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": "nomic-embed-text:latest"
                }
            },
            "vector_store": {
                "provider": "redis",
                "config": {
                    "collection_name": "mcp_memories",
                    "embedding_model_dims": 768
                }
            }
        },
        "server": {
            "name": "memory-mcp",
            "version": "1.0.0",
            "log_level": "INFO"
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration manager.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path or self._find_config_file()
        self._config = None
        self._load_config()
    
    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in standard locations."""
        possible_paths = [
            "config.json",
            "memory_mcp_config.json",
            os.path.expanduser("~/.memory_mcp/config.json"),
            "/etc/memory_mcp/config.json"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found configuration file: {path}")
                return path
        
        logger.info("No configuration file found, using defaults")
        return None
    
    def _load_config(self):
        """Load configuration from file or use defaults."""
        self._config = self.DEFAULT_CONFIG.copy()
        
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                
                # Validate that loaded config is a dictionary
                if not isinstance(file_config, dict):
                    raise ValueError("Configuration file must contain a JSON object")
                
                self._merge_config(self._config, file_config)
                logger.info(f"Loaded configuration from {self.config_path}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config file {self.config_path}: {e}")
                logger.info("Using default configuration")
            except FileNotFoundError:
                logger.error(f"Configuration file not found: {self.config_path}")
                logger.info("Using default configuration")
            except PermissionError:
                logger.error(f"Permission denied reading config file: {self.config_path}")
                logger.info("Using default configuration")
            except Exception as e:
                logger.error(f"Unexpected error loading config file {self.config_path}: {e}")
                logger.info("Using default configuration")
        
        # Override with environment variables
        try:
            self._load_env_overrides()
        except Exception as e:
            logger.error(f"Error loading environment variable overrides: {e}")
            # Continue with current config
        
        # Validate configuration
        try:
            self._validate_config()
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Recursively merge configuration dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _load_env_overrides(self):
        """Load configuration overrides from environment variables."""
        env_mappings = {
            "REDIS_URL": ("redis", "url"),
            "REDIS_DB": ("redis", "db"),
            "REDIS_COLLECTION": ("redis", "collection_name"),
            "MCP_SERVER_NAME": ("server", "name"),
            "MCP_LOG_LEVEL": ("server", "log_level"),
            "OLLAMA_MODEL": ("mem0", "llm", "config", "model"),
            "OLLAMA_EMBED_MODEL": ("mem0", "embedder", "config", "model")
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_config(self._config, config_path, value)
                logger.info(f"Override from {env_var}: {config_path}")
    
    def _set_nested_config(self, config: Dict[str, Any], path: tuple, value: Any):
        """Set a nested configuration value."""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Convert string values to appropriate types
        if path[-1] == "db" and isinstance(value, str):
            value = int(value)
        
        current[path[-1]] = value
    
    def _validate_config(self):
        """Validate the loaded configuration."""
        required_sections = ["redis", "mem0", "server"]
        
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate Redis configuration
        redis_config = self._config["redis"]
        if not redis_config.get("url"):
            raise ValueError("Redis URL is required")
        
        # Validate Redis URL format
        redis_url = redis_config["url"]
        if not redis_url.startswith(("redis://", "rediss://")):
            raise ValueError("Redis URL must start with 'redis://' or 'rediss://'")
        
        # Validate collection name
        collection_name = redis_config.get("collection_name")
        if not collection_name or not isinstance(collection_name, str):
            raise ValueError("Redis collection_name must be a non-empty string")
        
        # Validate mem0 configuration
        mem0_config = self._config["mem0"]
        if "llm" not in mem0_config or "embedder" not in mem0_config:
            raise ValueError("mem0 configuration must include 'llm' and 'embedder' sections")
        
        # Validate LLM configuration
        llm_config = mem0_config["llm"]
        if not llm_config.get("provider"):
            raise ValueError("mem0 LLM provider is required")
        
        if "config" not in llm_config:
            raise ValueError("mem0 LLM config section is required")
        
        # Validate embedder configuration
        embedder_config = mem0_config["embedder"]
        if not embedder_config.get("provider"):
            raise ValueError("mem0 embedder provider is required")
        
        if "config" not in embedder_config:
            raise ValueError("mem0 embedder config section is required")
        
        # Validate server configuration
        server_config = self._config["server"]
        if not server_config.get("name"):
            raise ValueError("Server name is required")
        
        if not server_config.get("version"):
            raise ValueError("Server version is required")
        
        # Validate log level
        log_level = server_config.get("log_level", "INFO")
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_log_levels:
            raise ValueError(f"Invalid log level '{log_level}'. Must be one of: {valid_log_levels}")
        
        logger.info("Configuration validation passed")
    
    def get_config(self) -> Dict[str, Any]:
        """Get the complete configuration."""
        return self._config.copy()
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis-specific configuration."""
        return self._config["redis"].copy()
    
    def get_mem0_config(self) -> Dict[str, Any]:
        """Get mem0-specific configuration."""
        return self._config["mem0"].copy()
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server-specific configuration."""
        return self._config["server"].copy()
    
    def create_sample_config(self, output_path: str = "config.json"):
        """Create a sample configuration file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(self.DEFAULT_CONFIG, f, indent=2)
            logger.info(f"Sample configuration created at {output_path}")
        except Exception as e:
            logger.error(f"Error creating sample config: {e}")
            raise
    
    def reload_config(self):
        """Reload configuration from file."""
        try:
            self._load_config()
            logger.info("Configuration reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            raise
    
    def validate_config_file(self, config_path: str) -> bool:
        """Validate a configuration file without loading it.
        
        Args:
            config_path: Path to configuration file to validate
            
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        try:
            if not os.path.exists(config_path):
                logger.error(f"Configuration file does not exist: {config_path}")
                return False
            
            with open(config_path, 'r') as f:
                file_config = json.load(f)
            
            if not isinstance(file_config, dict):
                logger.error("Configuration file must contain a JSON object")
                return False
            
            # Create a temporary config for validation
            temp_config = self.DEFAULT_CONFIG.copy()
            self._merge_config(temp_config, file_config)
            
            # Validate the merged configuration
            original_config = self._config
            self._config = temp_config
            try:
                self._validate_config()
                logger.info(f"Configuration file {config_path} is valid")
                return True
            finally:
                self._config = original_config
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            return False
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


def create_default_config_file(path: str = "config.json"):
    """Utility function to create a default configuration file."""
    config_manager = ConfigManager()
    config_manager.create_sample_config(path)