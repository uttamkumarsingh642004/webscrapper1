"""
Configuration loader for web scraper.

Loads and manages configuration from YAML/JSON files.
"""

import yaml
import json
from typing import Any, Dict, Optional
from pathlib import Path
import os


class ConfigLoader:
    """
    Load and manage scraper configuration.

    Supports YAML and JSON formats with environment variable substitution
    and configuration merging.
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_file: Path to configuration file (YAML or JSON)
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}

        # Load default config
        self._load_default_config()

        # Load user config if provided
        if config_file:
            self.load_config(config_file)

    def _load_default_config(self) -> None:
        """Load default configuration."""
        default_config_path = Path(__file__).parent / "default_config.yaml"

        if default_config_path.exists():
            self.config = self._load_yaml(default_config_path)
        else:
            self.config = self._get_minimal_config()

    def _get_minimal_config(self) -> Dict[str, Any]:
        """
        Get minimal default configuration.

        Returns:
            Minimal configuration dictionary
        """
        return {
            "scraping": {
                "scraper_type": "auto",
                "timeout": 30,
                "max_retries": 3,
                "rate_limit": 1.0,
                "max_workers": 5
            },
            "request": {
                "headers": {},
                "rotate_user_agent": True
            },
            "export": {
                "format": "json",
                "output_file": "scraped_data.json"
            },
            "error_handling": {
                "log_level": "INFO",
                "continue_on_error": True
            }
        }

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """
        Load configuration from file.

        Args:
            config_file: Path to configuration file

        Returns:
            Configuration dictionary
        """
        config_path = Path(config_file)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        # Determine file type
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            user_config = self._load_yaml(config_path)
        elif config_path.suffix.lower() == '.json':
            user_config = self._load_json(config_path)
        else:
            raise ValueError(f"Unsupported config file format: {config_path.suffix}")

        # Merge with default config
        self.config = self._merge_configs(self.config, user_config)

        # Substitute environment variables
        self.config = self._substitute_env_vars(self.config)

        return self.config

    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """
        Load YAML configuration file.

        Args:
            file_path: Path to YAML file

        Returns:
            Configuration dictionary
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """
        Load JSON configuration file.

        Args:
            file_path: Path to JSON file

        Returns:
            Configuration dictionary
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries.

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration
        """
        merged = base.copy()

        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged

    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute environment variables in configuration.

        Replaces ${VAR_NAME} with environment variable value.

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with substituted values
        """
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Replace ${VAR_NAME} with environment variable
            import re
            pattern = r'\$\{([^}]+)\}'

            def replace_var(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))

            return re.sub(pattern, replace_var, config)
        else:
            return config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key (supports dot notation, e.g., "scraping.timeout")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.

        Args:
            updates: Dictionary of updates
        """
        self.config = self._merge_configs(self.config, updates)

    def save(self, file_path: str, format: str = "yaml") -> None:
        """
        Save configuration to file.

        Args:
            file_path: Path to save configuration
            format: Format to save (yaml or json)
        """
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == "yaml":
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
        elif format.lower() == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Get configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        return self.config.copy()

    def __getitem__(self, key: str) -> Any:
        """Get configuration value using dictionary syntax."""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set configuration value using dictionary syntax."""
        self.set(key, value)

    def __repr__(self) -> str:
        """String representation."""
        return f"ConfigLoader(config_file={self.config_file})"


def load_config(config_file: Optional[str] = None) -> ConfigLoader:
    """
    Convenience function to load configuration.

    Args:
        config_file: Path to configuration file

    Returns:
        ConfigLoader instance
    """
    return ConfigLoader(config_file)
