#!/usr/bin/env python3
"""
Entry point script for Memory MCP Server

Usage:
    python run_server.py [--config CONFIG_PATH]
"""

import argparse
import asyncio
import sys
from memory_mcp_server import MemoryMCPServer


def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Memory MCP Server")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a sample configuration file and exit"
    )
    
    args = parser.parse_args()
    
    if args.create_config:
        from config_manager import create_default_config_file
        create_default_config_file()
        print("Sample configuration file created: config.json")
        sys.exit(0)
    
    try:
        server = MemoryMCPServer(config_path=args.config)
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()