#!/usr/bin/env python3
"""
Memory MCP Server

A Model Context Protocol server that provides memory management capabilities
using the mem0 Python library with Redis as the backend database.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from config_manager import ConfigManager
from memory_manager import MemoryManager
from error_handler import (
    ErrorHandler, MCPError, ValidationError, ConnectionError, MemoryError,
    ErrorCode, setup_logging
)

logger = logging.getLogger(__name__)


class MemoryMCPServer:
    """Main MCP server class that handles memory operations."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the Memory MCP Server.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_manager = ConfigManager(config_path)
        self.memory_manager = None
        self._initialized = False
        
        # Initialize error handler
        self.error_handler = ErrorHandler("memory_mcp_server")
        
        # Set up logging based on configuration
        server_config = self.config_manager.get_server_config()
        log_level = server_config.get("log_level", "INFO")
        setup_logging(log_level)
        
        # Get server configuration
        server_name = server_config.get("name", "memory-mcp")
        
        self.server = Server(server_name)
        self._register_tools()
        
        logger.info(f"MemoryMCPServer initialized with name: {server_name}")
    
    def _register_tools(self):
        """Register MCP tools with the server."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available memory management tools."""
            return [
                Tool(
                    name="add_memory",
                    description="Add a new memory to the system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Memory content to store"
                            },
                            "user_id": {
                                "type": "string", 
                                "description": "User identifier"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata for the memory"
                            }
                        },
                        "required": ["content", "user_id"]
                    }
                ),
                Tool(
                    name="get_memory",
                    description="Retrieve memories based on query",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for memories"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User identifier"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 10
                            }
                        },
                        "required": ["query", "user_id"]
                    }
                ),
                Tool(
                    name="delete_memory",
                    description="Delete a specific memory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "memory_id": {
                                "type": "string",
                                "description": "Memory identifier to delete"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User identifier"
                            }
                        },
                        "required": ["memory_id", "user_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                # Log operation start
                user_id = arguments.get("user_id", "unknown")
                self.error_handler.log_operation_start(f"tool_{name}", user_id, {"arguments": arguments})
                
                if name == "add_memory":
                    result = await self._handle_add_memory(arguments)
                elif name == "get_memory":
                    result = await self._handle_get_memory(arguments)
                elif name == "delete_memory":
                    result = await self._handle_delete_memory(arguments)
                else:
                    raise MCPError(ErrorCode.TOOL_NOT_FOUND, f"Unknown tool: {name}")
                
                # Log successful operation
                self.error_handler.log_operation(f"tool_{name}", user_id)
                return result
                
            except Exception as e:
                # Use error handler for consistent error formatting
                return self.error_handler.format_error_response(e)
    
    async def _handle_add_memory(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle add_memory tool calls.
        
        Args:
            arguments: Tool arguments containing content, user_id, and optional metadata
            
        Returns:
            List[TextContent]: MCP response with memory ID or error message
        """
        # Validate required arguments
        if "content" not in arguments:
            raise ValidationError("'content' parameter is required", field="content")
        
        if "user_id" not in arguments:
            raise ValidationError("'user_id' parameter is required", field="user_id")
        
        content = arguments["content"]
        user_id = arguments["user_id"]
        metadata = arguments.get("metadata")
        
        # Validate parameter types
        if not isinstance(content, str):
            raise ValidationError("'content' must be a string", field="content", value=type(content).__name__)
        
        if not isinstance(user_id, str):
            raise ValidationError("'user_id' must be a string", field="user_id", value=type(user_id).__name__)
        
        if metadata is not None and not isinstance(metadata, dict):
            raise ValidationError("'metadata' must be a dictionary", field="metadata", value=type(metadata).__name__)
        
        # Ensure memory manager is initialized
        if not self.memory_manager:
            raise MCPError(ErrorCode.SERVER_NOT_INITIALIZED, "Memory manager not initialized")
        
        try:
            # Add memory using MemoryManager
            memory_id = await self.memory_manager.add_memory(
                content=content,
                user_id=user_id,
                metadata=metadata
            )
            
            # Return success response
            return [TextContent(
                type="text",
                text=f"Memory added successfully with ID: {memory_id}"
            )]
            
        except Exception as e:
            # Re-raise as MemoryError for consistent handling
            raise MemoryError(ErrorCode.MEMORY_ADD_FAILED, f"Failed to add memory: {str(e)}", user_id=user_id)
    
    async def _handle_get_memory(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_memory tool calls.
        
        Args:
            arguments: Tool arguments containing query, user_id, and optional limit
            
        Returns:
            List[TextContent]: MCP response with memory records or error message
        """
        # Validate required arguments
        if "query" not in arguments:
            raise ValidationError("'query' parameter is required", field="query")
        
        if "user_id" not in arguments:
            raise ValidationError("'user_id' parameter is required", field="user_id")
        
        query = arguments["query"]
        user_id = arguments["user_id"]
        limit = arguments.get("limit", 10)
        
        # Validate parameter types
        if not isinstance(query, str):
            raise ValidationError("'query' must be a string", field="query", value=type(query).__name__)
        
        if not isinstance(user_id, str):
            raise ValidationError("'user_id' must be a string", field="user_id", value=type(user_id).__name__)
        
        if not isinstance(limit, int):
            raise ValidationError("'limit' must be an integer", field="limit", value=type(limit).__name__)
        
        # Ensure memory manager is initialized
        if not self.memory_manager:
            raise MCPError(ErrorCode.SERVER_NOT_INITIALIZED, "Memory manager not initialized")
        
        try:
            # Retrieve memories using MemoryManager
            memories = await self.memory_manager.get_memories(
                query=query,
                user_id=user_id,
                limit=limit
            )
            
            # Format results according to MCP protocol standards
            if not memories:
                return [TextContent(
                    type="text",
                    text="No memories found matching the query"
                )]
            
            # Format memory records for response
            result_text = f"Found {len(memories)} memory(ies):\n\n"
            
            for i, memory in enumerate(memories, 1):
                result_text += f"Memory {i}:\n"
                result_text += f"  ID: {memory.get('id', 'unknown')}\n"
                result_text += f"  Content: {memory.get('content', '')}\n"
                result_text += f"  Relevance Score: {memory.get('relevance_score', 0.0):.3f}\n"
                result_text += f"  Created: {memory.get('created_at', 'unknown')}\n"
                
                # Include metadata if present
                metadata = memory.get('metadata', {})
                if metadata:
                    result_text += f"  Metadata: {metadata}\n"
                
                result_text += "\n"
            
            return [TextContent(
                type="text",
                text=result_text.strip()
            )]
            
        except Exception as e:
            # Re-raise as MemoryError for consistent handling
            raise MemoryError(ErrorCode.MEMORY_SEARCH_FAILED, f"Failed to search memories: {str(e)}", user_id=user_id)
    
    async def _handle_delete_memory(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle delete_memory tool calls.
        
        Args:
            arguments: Tool arguments containing memory_id and user_id
            
        Returns:
            List[TextContent]: MCP response with deletion status or error message
        """
        # Validate required arguments
        if "memory_id" not in arguments:
            raise ValidationError("'memory_id' parameter is required", field="memory_id")
        
        if "user_id" not in arguments:
            raise ValidationError("'user_id' parameter is required", field="user_id")
        
        memory_id = arguments["memory_id"]
        user_id = arguments["user_id"]
        
        # Validate parameter types
        if not isinstance(memory_id, str):
            raise ValidationError("'memory_id' must be a string", field="memory_id", value=type(memory_id).__name__)
        
        if not isinstance(user_id, str):
            raise ValidationError("'user_id' must be a string", field="user_id", value=type(user_id).__name__)
        
        # Ensure memory manager is initialized
        if not self.memory_manager:
            raise MCPError(ErrorCode.SERVER_NOT_INITIALIZED, "Memory manager not initialized")
        
        try:
            # Delete memory using MemoryManager
            deletion_successful = await self.memory_manager.delete_memory(
                memory_id=memory_id,
                user_id=user_id
            )
            
            # Handle success/failure responses
            if deletion_successful:
                return [TextContent(
                    type="text",
                    text=f"Memory with ID '{memory_id}' deleted successfully"
                )]
            else:
                # Memory not found is not an error, just return appropriate message
                return [TextContent(
                    type="text",
                    text=f"Memory with ID '{memory_id}' not found or could not be deleted"
                )]
            
        except Exception as e:
            # Re-raise as MemoryError for consistent handling
            raise MemoryError(ErrorCode.MEMORY_DELETE_FAILED, f"Failed to delete memory: {str(e)}", memory_id=memory_id, user_id=user_id)
    
    async def initialize(self):
        """Initialize the memory manager and server components."""
        if self._initialized:
            logger.info("MemoryMCPServer already initialized")
            return
            
        try:
            # Validate configuration before initialization
            config = self.config_manager.get_config()
            logger.info("Configuration loaded and validated successfully")
            
            # Initialize memory manager
            self.memory_manager = MemoryManager(config)
            await self.memory_manager.initialize()
            
            self._initialized = True
            logger.info("Memory MCP Server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            self._initialized = False
            raise
    
    def is_initialized(self) -> bool:
        """Check if the server is initialized.
        
        Returns:
            bool: True if server is initialized, False otherwise
        """
        return self._initialized
    
    async def shutdown(self):
        """Gracefully shutdown the server."""
        try:
            logger.info("Shutting down Memory MCP Server...")
            
            # Clean up memory manager if needed
            if self.memory_manager:
                # Add any cleanup logic here if needed
                pass
            
            self._initialized = False
            logger.info("Memory MCP Server shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during server shutdown: {e}")
            raise
    
    async def run(self):
        """Run the MCP server."""
        try:
            # Initialize server components
            await self.initialize()
            
            # Get server configuration
            server_config = self.config_manager.get_server_config()
            server_name = server_config.get("name", "memory-mcp")
            server_version = server_config.get("version", "1.0.0")
            
            logger.info(f"Starting {server_name} v{server_version}")
            
            # Run the MCP server
            async with stdio_server() as (read_stream, write_stream):
                try:
                    await self.server.run(
                        read_stream,
                        write_stream,
                        InitializationOptions(
                            server_name=server_name,
                            server_version=server_version,
                            capabilities=self.server.get_capabilities(
                                notification_options=NotificationOptions(),
                                experimental_capabilities={}
                            )
                        )
                    )
                except* Exception as group:
                    # Surface the inner errors from the TaskGroup so users see the real cause
                    for exc in group.exceptions:
                        logger.exception("error occured: ")
                        logger.error(f"Background task error: {exc}")
                    raise RuntimeError(
                        "Server failed to start due to background task errors. "
                        "Review logs above for details."
                    )
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            await self.shutdown()


async def main():
    """Main entry point for the server."""
    server = MemoryMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
