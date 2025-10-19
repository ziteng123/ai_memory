#!/usr/bin/env python3
"""
Memory MCP Server - Main Entry Point

Command-line interface for starting the Memory MCP Server with
configuration file loading support and graceful shutdown handling.
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from memory_mcp_server import MemoryMCPServer
from config_manager import ConfigManager, create_default_config_file
from error_handler import setup_logging

logger = logging.getLogger(__name__)


class ServerRunner:
    """Handles server lifecycle and command-line interface."""
    
    def __init__(self):
        self.server: Optional[MemoryMCPServer] = None
        self.shutdown_event = asyncio.Event()
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_event.set()
        
        # Handle common shutdown signals
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Handle SIGHUP for configuration reload (Unix only)
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    async def run_server(self, config_path: Optional[str] = None):
        """Run the MCP server with configuration.
        
        Args:
            config_path: Optional path to configuration file
        """
        try:
            # Initialize server
            self.server = MemoryMCPServer(config_path)
            
            # Set up signal handlers
            self.setup_signal_handlers()
            
            # Create server task
            server_task = asyncio.create_task(self.server.run())
            
            # Create shutdown monitoring task
            shutdown_task = asyncio.create_task(self.shutdown_event.wait())
            
            # Wait for either server completion or shutdown signal
            done, pending = await asyncio.wait(
                [server_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # If shutdown was requested, ensure server is properly shut down
            if shutdown_task in done:
                logger.info("Shutdown requested, stopping server...")
                if self.server:
                    await self.server.shutdown()
            
            # Check if server task completed with an exception
            if server_task in done:
                try:
                    await server_task
                except Exception as e:
                    logger.error(f"Server task failed: {e}")
                    raise
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            if self.server:
                try:
                    await self.server.shutdown()
                except Exception as e:
                    logger.error(f"Error during server shutdown: {e}")


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Memory MCP Server - Provides memory management capabilities via MCP protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Start server with default configuration
  %(prog)s -c config.json           # Start server with custom configuration
  %(prog)s --create-config          # Create sample configuration file
  %(prog)s --validate-config config.json  # Validate configuration file
  %(prog)s --log-level DEBUG        # Start with debug logging
        """
    )
    
    parser.add_argument(
        "-c", "--config",
        type=str,
        help="Path to configuration file (default: auto-discover)"
    )
    
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a sample configuration file and exit"
    )
    
    parser.add_argument(
        "--validate-config",
        type=str,
        metavar="CONFIG_FILE",
        help="Validate configuration file and exit"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (overrides config file setting)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Memory MCP Server 1.0.0"
    )
    
    return parser


def validate_config_file(config_path: str) -> bool:
    """Validate a configuration file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        config_manager = ConfigManager()
        is_valid = config_manager.validate_config_file(config_path)
        
        if is_valid:
            print(f"✓ Configuration file '{config_path}' is valid")
            return True
        else:
            print(f"✗ Configuration file '{config_path}' is invalid")
            return False
            
    except Exception as e:
        print(f"✗ Error validating configuration file '{config_path}': {e}")
        return False


def create_sample_config(output_path: str = "config.json") -> bool:
    """Create a sample configuration file.
    
    Args:
        output_path: Path where to create the configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if file already exists
        if Path(output_path).exists():
            response = input(f"Configuration file '{output_path}' already exists. Overwrite? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Configuration file creation cancelled")
                return False
        
        create_default_config_file(output_path)
        print(f"✓ Sample configuration file created at '{output_path}'")
        print(f"  Edit the file to customize Redis connection and mem0 settings")
        return True
        
    except Exception as e:
        print(f"✗ Error creating configuration file: {e}")
        return False


async def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle create-config command
    if args.create_config:
        success = create_sample_config()
        sys.exit(0 if success else 1)
    
    # Handle validate-config command
    if args.validate_config:
        success = validate_config_file(args.validate_config)
        sys.exit(0 if success else 1)
    
    # Set up logging
    log_level = args.log_level or "INFO"
    setup_logging(log_level)
    
    # Log startup information
    logger.info("Starting Memory MCP Server...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Configuration file: {args.config or 'auto-discover'}")
    logger.info(f"Log level: {log_level}")
    
    # Validate configuration file if specified
    if args.config:
        if not Path(args.config).exists():
            logger.error(f"Configuration file not found: {args.config}")
            sys.exit(1)
        
        if not validate_config_file(args.config):
            logger.error(f"Invalid configuration file: {args.config}")
            sys.exit(1)
    
    # Run the server
    runner = ServerRunner()
    try:
        await runner.run_server(args.config)
        logger.info("Server shutdown complete")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)