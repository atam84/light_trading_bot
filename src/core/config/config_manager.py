# src/core/config/config_manager.py

import asyncio
import logging
import json
import yaml
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import copy

class ConfigScope(Enum):
    """Configuration scope levels"""
    SYSTEM = "system"
    USER = "user"
    STRATEGY = "strategy"
    SESSION = "session"

class ConfigFormat(Enum):
    """Configuration file formats"""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"

@dataclass
class ConfigRule:
    """Configuration validation rule"""
    key: str
    rule_type: str  # required, type, range, choices, custom
    description: str
    rule_data: Any = None
    validator_func: Optional[Callable] = None
    error_message: str = ""

@dataclass
class ConfigChange:
    """Configuration change record"""
    change_id: str
    scope: ConfigScope
    key: str
    old_value: Any
    new_value: Any
    changed_by: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""

class ConfigManager:
    """Centralized configuration management system"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Configuration storage by scope
        self._configs: Dict[ConfigScope, Dict[str, Any]] = {
            scope: {} for scope in ConfigScope
        }
        
        # Validation rules
        self._validation_rules: Dict[str, ConfigRule] = {}
        
        # Change tracking
        self._change_history: List[ConfigChange] = []
        self._watchers: Dict[str, List[Callable]] = {}
        
        # File paths
        self._config_files = {
            ConfigScope.SYSTEM: self.config_dir / "system.yaml",
            ConfigScope.USER: self.config_dir / "user.yaml",
            ConfigScope.STRATEGY: self.config_dir / "strategies.yaml",
            ConfigScope.SESSION: self.config_dir / "session.json"
        }
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize default validation rules
        self._initialize_default_rules()
        
        self.logger.info(f"Config manager initialized with directory: {self.config_dir}")
    
    def _initialize_default_rules(self):
        """Initialize default validation rules"""
        # System configuration rules
        self.add_validation_rule(ConfigRule(
            key="trading.mode",
            rule_type="choices",
            description="Trading mode selection",
            rule_data=["live", "paper", "backtest"],
            error_message="Trading mode must be 'live', 'paper', or 'backtest'"
        ))
        
        self.add_validation_rule(ConfigRule(
            key="trading.default_exchange",
            rule_type="choices",
            description="Default exchange",
            rule_data=["kucoin", "binance", "okx", "bybit"],
            error_message="Exchange must be one of supported exchanges"
        ))
        
        self.add_validation_rule(ConfigRule(
            key="risk_management.max_allocation_percentage",
            rule_type="range",
            description="Maximum balance allocation percentage",
            rule_data={"min": 0.0, "max": 1.0},
            error_message="Allocation percentage must be between 0 and 1"
        ))
        
        self.add_validation_rule(ConfigRule(
            key="risk_management.max_trade_amount",
            rule_type="type",
            description="Maximum trade amount",
            rule_data=float,
            error_message="Max trade amount must be a number"
        ))
        
        # Data configuration rules
        self.add_validation_rule(ConfigRule(
            key="data.cache_ttl",
            rule_type="range",
            description="Cache TTL in seconds",
            rule_data={"min": 60, "max": 3600},
            error_message="Cache TTL must be between 60 and 3600 seconds"
        ))
        
        self.logger.info(f"Initialized {len(self._validation_rules)} default validation rules")
    
    async def initialize(self) -> bool:
        """Initialize configuration manager"""
        try:
            # Load all configuration files
            await self._load_all_configs()
            
            # Apply environment variable overrides
            self._apply_env_overrides()
            
            # Validate all configurations
            validation_errors = await self._validate_all_configs()
            if validation_errors:
                self.logger.error(f"Configuration validation errors: {validation_errors}")
                return False
            
            # Set up default configurations if missing
            await self._ensure_default_configs()
            
            self.logger.info("Configuration manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration manager: {e}")
            return False
    
    async def _load_all_configs(self):
        """Load all configuration files"""
        for scope, file_path in self._config_files.items():
            try:
                if file_path.exists():
                    config_data = await self._load_config_file(file_path)
                    self._configs[scope] = config_data
                    self.logger.debug(f"Loaded {scope.value} config from {file_path}")
                else:
                    self._configs[scope] = {}
                    self.logger.debug(f"No config file found for {scope.value}, using empty config")
                    
            except Exception as e:
                self.logger.error(f"Failed to load {scope.value} config: {e}")
                self._configs[scope] = {}
    
    async def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif file_path.suffix.lower() == '.json':
                    return json.load(f) or {}
                else:
                    raise ValueError(f"Unsupported config file format: {file_path.suffix}")
                    
        except Exception as e:
            self.logger.error(f"Error loading config file {file_path}: {e}")
            return {}
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        try:
            # Environment variables with TRADING_BOT_ prefix override config
            env_prefix = "TRADING_BOT_"
            
            for env_key, env_value in os.environ.items():
                if env_key.startswith(env_prefix):
                    # Convert env key to config key (TRADING_BOT_DATA_CACHE_TTL -> data.cache_ttl)
                    config_key = env_key[len(env_prefix):].lower().replace('_', '.')
                    
                    # Try to parse value as appropriate type
                    parsed_value = self._parse_env_value(env_value)
                    
                    # Set in system config
                    self._set_nested_value(self._configs[ConfigScope.SYSTEM], config_key, parsed_value)
                    
                    self.logger.debug(f"Applied env override: {config_key} = {parsed_value}")
                    
        except Exception as e:
            self.logger.error(f"Error applying environment overrides: {e}")
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type"""
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # Return as string
        return value
    
    def _set_nested_value(self, config_dict: Dict[str, Any], key: str, value: Any):
        """Set nested configuration value using dot notation"""
        keys = key.split('.')
        current = config_dict
        
        # Navigate to parent of target key
        for key_part in keys[:-1]:
            if key_part not in current:
                current[key_part] = {}
            current = current[key_part]
        
        # Set the final value
        current[keys[-1]] = value
    
    def _get_nested_value(self, config_dict: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Get nested configuration value using dot notation"""
        keys = key.split('.')
        current = config_dict
        
        try:
            for key_part in keys:
                current = current[key_part]
            return current
        except (KeyError, TypeError):
            return default
    
    async def _validate_all_configs(self) -> List[str]:
        """Validate all configurations against rules"""
        errors = []
        
        for scope, config_data in self._configs.items():
            scope_errors = await self._validate_config(config_data, scope)
            if scope_errors:
                errors.extend([f"{scope.value}: {error}" for error in scope_errors])
        
        return errors
    
    async def _validate_config(self, config_data: Dict[str, Any], scope: ConfigScope) -> List[str]:
        """Validate configuration data against rules"""
        errors = []
        
        for rule_key, rule in self._validation_rules.items():
            try:
                value = self._get_nested_value(config_data, rule_key)
                
                # Check if required value is missing
                if rule.rule_type == "required" and value is None:
                    errors.append(f"Required configuration missing: {rule_key}")
                    continue
                
                # Skip validation if value is None and not required
                if value is None:
                    continue
                
                # Validate based on rule type
                if rule.rule_type == "type":
                    if not isinstance(value, rule.rule_data):
                        errors.append(rule.error_message or f"Invalid type for {rule_key}")
                
                elif rule.rule_type == "range":
                    if isinstance(rule.rule_data, dict):
                        min_val = rule.rule_data.get("min")
                        max_val = rule.rule_data.get("max")
                        
                        if min_val is not None and value < min_val:
                            errors.append(rule.error_message or f"{rule_key} below minimum: {min_val}")
                        
                        if max_val is not None and value > max_val:
                            errors.append(rule.error_message or f"{rule_key} above maximum: {max_val}")
                
                elif rule.rule_type == "choices":
                    if value not in rule.rule_data:
                        errors.append(rule.error_message or f"Invalid choice for {rule_key}: {value}")
                
                elif rule.rule_type == "custom" and rule.validator_func:
                    if not rule.validator_func(value):
                        errors.append(rule.error_message or f"Custom validation failed for {rule_key}")
                        
            except Exception as e:
                errors.append(f"Validation error for {rule_key}: {e}")
        
        return errors
    
    async def _ensure_default_configs(self):
        """Ensure default configurations are set"""
        defaults = {
            ConfigScope.SYSTEM: {
                "trading": {
                    "mode": "paper",
                    "default_exchange": "kucoin",
                    "supported_timeframes": ["1m", "5m", "15m", "30m", "1h", "4h", "8h", "1d", "1w"],
                    "max_concurrent_trades": 10
                },
                "risk_management": {
                    "max_allocation_percentage": 0.5,
                    "max_trade_amount": 1000.0,
                    "max_positions": 10,
                    "default_stop_loss_pct": 0.05,
                    "default_take_profit_pct": 0.15
                },
                "data": {
                    "ccxt_gateway_url": "http://ccxt-bridge:3000",
                    "cache_enabled": True,
                    "cache_ttl": 300,
                    "request_timeout": 30
                },
                "logging": {
                    "level": "INFO",
                    "file": "logs/trading_bot.log",
                    "max_file_size": "10MB",
                    "backup_count": 5
                }
            },
            ConfigScope.USER: {
                "preferences": {
                    "timezone": "UTC",
                    "currency": "USD",
                    "theme": "dark"
                },
                "notifications": {
                    "telegram_enabled": False,
                    "email_enabled": False,
                    "trade_signals": True,
                    "execution_confirmations": True
                }
            },
            ConfigScope.STRATEGY: {
                "default_strategy": {
                    "name": "DefaultStrategy",
                    "enabled": False,
                    "symbols": ["BTC/USDT"],
                    "timeframe": "1h",
                    "risk_per_trade": 0.02
                }
            }
        }
        
        for scope, default_config in defaults.items():
            current_config = self._configs[scope]
            
            # Merge defaults with existing config
            merged_config = self._deep_merge(default_config, current_config)
            self._configs[scope] = merged_config
            
            # Save if changes were made
            if merged_config != current_config:
                await self._save_config(scope)
    
    def _deep_merge(self, default: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge default configuration with current configuration"""
        result = copy.deepcopy(default)
        
        for key, value in current.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result
    
    # Public API methods
    def get(self, key: str, default: Any = None, scope: Optional[ConfigScope] = None) -> Any:
        """Get configuration value"""
        if scope:
            # Get from specific scope
            return self._get_nested_value(self._configs[scope], key, default)
        else:
            # Search through scopes in priority order
            for scope in [ConfigScope.SESSION, ConfigScope.USER, ConfigScope.STRATEGY, ConfigScope.SYSTEM]:
                value = self._get_nested_value(self._configs[scope], key)
                if value is not None:
                    return value
            
            return default
    
    async def set(self, key: str, value: Any, scope: ConfigScope = ConfigScope.USER, 
                 changed_by: str = "system", reason: str = "") -> bool:
        """Set configuration value"""
        try:
            # Get old value for change tracking
            old_value = self._get_nested_value(self._configs[scope], key)
            
            # Validate new value
            validation_errors = await self._validate_single_key(key, value)
            if validation_errors:
                self.logger.error(f"Validation failed for {key}: {validation_errors}")
                return False
            
            # Set new value
            self._set_nested_value(self._configs[scope], key, value)
            
            # Record change
            change = ConfigChange(
                change_id=f"{scope.value}_{key}_{datetime.utcnow().timestamp()}",
                scope=scope,
                key=key,
                old_value=old_value,
                new_value=value,
                changed_by=changed_by,
                reason=reason
            )
            self._change_history.append(change)
            
            # Notify watchers
            await self._notify_watchers(key, old_value, value)
            
            # Save configuration
            await self._save_config(scope)
            
            self.logger.info(f"Configuration updated: {key} = {value} (scope: {scope.value})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set configuration {key}: {e}")
            return False
    
    async def _validate_single_key(self, key: str, value: Any) -> List[str]:
        """Validate a single configuration key"""
        if key in self._validation_rules:
            rule = self._validation_rules[key]
            temp_config = {key: value}
            return await self._validate_config(temp_config, ConfigScope.SYSTEM)
        
        return []  # No validation rule, assume valid
    
    def get_section(self, section: str, scope: Optional[ConfigScope] = None) -> Dict[str, Any]:
        """Get entire configuration section"""
        if scope:
            return self._get_nested_value(self._configs[scope], section, {})
        else:
            # Merge sections from all scopes
            result = {}
            for scope in [ConfigScope.SYSTEM, ConfigScope.STRATEGY, ConfigScope.USER, ConfigScope.SESSION]:
                section_data = self._get_nested_value(self._configs[scope], section, {})
                result = self._deep_merge(result, section_data)
            
            return result
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all configurations by scope"""
        return {scope.value: config.copy() for scope, config in self._configs.items()}
    
    def add_validation_rule(self, rule: ConfigRule):
        """Add configuration validation rule"""
        self._validation_rules[rule.key] = rule
        self.logger.debug(f"Added validation rule for {rule.key}")
    
    def remove_validation_rule(self, key: str) -> bool:
        """Remove validation rule"""
        if key in self._validation_rules:
            del self._validation_rules[key]
            self.logger.debug(f"Removed validation rule for {key}")
            return True
        return False
    
    # Watchers for configuration changes
    def add_watcher(self, key: str, callback: Callable[[str, Any, Any], None]):
        """Add configuration change watcher"""
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)
    
    def remove_watcher(self, key: str, callback: Callable):
        """Remove configuration change watcher"""
        if key in self._watchers:
            try:
                self._watchers[key].remove(callback)
            except ValueError:
                pass
    
    async def _notify_watchers(self, key: str, old_value: Any, new_value: Any):
        """Notify watchers of configuration changes"""
        # Notify exact key watchers
        if key in self._watchers:
            for callback in self._watchers[key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(key, old_value, new_value)
                    else:
                        callback(key, old_value, new_value)
                except Exception as e:
                    self.logger.error(f"Error in config watcher for {key}: {e}")
        
        # Notify wildcard watchers (e.g., "trading.*")
        for watch_key, callbacks in self._watchers.items():
            if watch_key.endswith('*') and key.startswith(watch_key[:-1]):
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(key, old_value, new_value)
                        else:
                            callback(key, old_value, new_value)
                    except Exception as e:
                        self.logger.error(f"Error in wildcard config watcher {watch_key}: {e}")
    
    # File operations
    async def _save_config(self, scope: ConfigScope):
        """Save configuration to file"""
        try:
            file_path = self._config_files[scope]
            config_data = self._configs[scope]
            
            # Create backup if file exists
            if file_path.exists():
                backup_path = file_path.with_suffix(f'.backup.{int(datetime.utcnow().timestamp())}')
                file_path.rename(backup_path)
            
            # Save configuration
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                elif file_path.suffix.lower() == '.json':
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Saved {scope.value} configuration to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save {scope.value} configuration: {e}")
    
    async def reload_configs(self) -> bool:
        """Reload all configurations from files"""
        try:
            await self._load_all_configs()
            validation_errors = await self._validate_all_configs()
            
            if validation_errors:
                self.logger.error(f"Configuration validation errors after reload: {validation_errors}")
                return False
            
            self.logger.info("Configurations reloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload configurations: {e}")
            return False
    
    async def export_config(self, scope: ConfigScope, file_path: str, format: ConfigFormat = ConfigFormat.YAML) -> bool:
        """Export configuration to file"""
        try:
            config_data = self._configs[scope]
            export_path = Path(file_path)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                if format == ConfigFormat.YAML:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                elif format == ConfigFormat.JSON:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Exported {scope.value} configuration to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    # Change history and rollback
    def get_change_history(self, key: Optional[str] = None, limit: int = 100) -> List[ConfigChange]:
        """Get configuration change history"""
        changes = self._change_history
        
        if key:
            changes = [change for change in changes if change.key == key]
        
        return sorted(changes, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    async def rollback_change(self, change_id: str) -> bool:
        """Rollback a configuration change"""
        try:
            # Find the change
            change = None
            for c in self._change_history:
                if c.change_id == change_id:
                    change = c
                    break
            
            if not change:
                self.logger.error(f"Change not found: {change_id}")
                return False
            
            # Rollback to old value
            success = await self.set(
                key=change.key,
                value=change.old_value,
                scope=change.scope,
                changed_by="rollback",
                reason=f"Rollback of change {change_id}"
            )
            
            if success:
                self.logger.info(f"Rolled back configuration change: {change_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to rollback change {change_id}: {e}")
            return False
    
    # Status and health
    def get_status(self) -> Dict[str, Any]:
        """Get configuration manager status"""
        return {
            "config_scopes": {
                scope.value: {
                    "keys": len(config),
                    "file_exists": self._config_files[scope].exists()
                }
                for scope, config in self._configs.items()
            },
            "validation_rules": len(self._validation_rules),
            "watchers": sum(len(callbacks) for callbacks in self._watchers.values()),
            "change_history": len(self._change_history),
            "last_change": self._change_history[-1].timestamp.isoformat() if self._change_history else None
        }
    
    def is_healthy(self) -> bool:
        """Check if configuration manager is healthy"""
        try:
            # Check if all required config files are readable
            for scope, file_path in self._config_files.items():
                if file_path.exists() and not os.access(file_path, os.R_OK):
                    return False
            
            # Check if configurations are valid
            validation_errors = []
            for scope, config_data in self._configs.items():
                errors = []
                # Simple sync validation for health check
                for rule_key, rule in self._validation_rules.items():
                    if rule.rule_type == "required":
                        value = self._get_nested_value(config_data, rule_key)
                        if value is None:
                            errors.append(f"Required config missing: {rule_key}")
                
                validation_errors.extend(errors)
            
            return len(validation_errors) == 0
            
        except Exception:
            return False
    
    async def cleanup(self):
        """Cleanup configuration manager"""
        # Save all configurations
        for scope in ConfigScope:
            await self._save_config(scope)
        
        # Clear change history
        self._change_history.clear()
        self._watchers.clear()
        
        self.logger.info("Configuration manager cleaned up")