"""
Memory Manager for Memory MCP Server

Provides a wrapper around the mem0 library for memory operations
with Redis backend integration and error handling.
"""

import logging
from typing import Any, Dict, List, Optional
import asyncio
from mem0 import Memory
import redis
from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class MemoryManagerError(Exception):
    """Base exception for MemoryManager errors."""
    pass


class ConnectionError(MemoryManagerError):
    """Raised when Redis connection fails."""
    pass


class ValidationError(MemoryManagerError):
    """Raised when input validation fails."""
    pass


class MemoryManager:
    """Manages memory operations using mem0 with Redis backend."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Memory Manager.
        
        Args:
            config: Configuration dictionary containing Redis and mem0 settings
        """
        self.config = config
        self.redis_config = config.get("redis", {})
        self.mem0_config = config.get("mem0", {})
        
        self._memory = None
        self._redis_client = None
        self._initialized = False
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate the configuration parameters."""
        if not self.redis_config.get("url"):
            raise ValidationError("Redis URL is required in configuration")
        
        if not self.mem0_config.get("llm"):
            raise ValidationError("mem0 LLM configuration is required")
        
        if not self.mem0_config.get("embedder"):
            raise ValidationError("mem0 embedder configuration is required")
        
        logger.info("Configuration validation passed")
    
    async def initialize(self):
        """Initialize mem0 and Redis connections."""
        if self._initialized:
            logger.info("MemoryManager already initialized")
            return
        
        try:
            # Initialize Redis client for connection validation
            await self._init_redis_client()
            
            # Initialize mem0 with Redis configuration
            await self._init_mem0()
            
            self._initialized = True
            logger.info("MemoryManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MemoryManager: {e}")
            raise ConnectionError(f"Initialization failed: {str(e)}")
    
    async def _init_redis_client(self):
        """Initialize and validate Redis connection."""
        try:
            redis_url = self.redis_config["url"]
            redis_db = self.redis_config.get("db", 0)
            
            # Create Redis client
            self._redis_client = redis.from_url(
                redis_url,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await asyncio.get_event_loop().run_in_executor(
                None, self._redis_client.ping
            )
            
            logger.info(f"Redis connection established: {redis_url}")
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis connection failed: {e}")
            raise ConnectionError(f"Failed to connect to Redis: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Redis initialization: {e}")
            raise ConnectionError(f"Redis initialization error: {str(e)}")
    
    async def _init_mem0(self):
        """Initialize mem0 with configuration."""
        try:
            # Prepare mem0 configuration
            mem0_init_config = {
                "llm": self.mem0_config["llm"],
                "embedder": self.mem0_config["embedder"]
            }
            
            # Add vector store configuration if present
            if "vector_store" in self.mem0_config:
                vector_config = self.mem0_config["vector_store"].copy()
                vector_config["config"] = vector_config.get("config", {}).copy()
                # Update vector store config with Redis URL
                if vector_config.get("provider") == "redis":
                    vector_config["config"]["redis_url"] = self.redis_config["url"]
                    vector_config["config"]["collection_name"] = self.redis_config.get(
                        "collection_name", "mcp_memories"
                    )
                mem0_init_config["vector_store"] = vector_config
            
            # Initialize mem0 using the library helper to validate config schema
            self._memory = Memory.from_config(mem0_init_config)
            
            logger.info("mem0 initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize mem0: {e}")
            raise ConnectionError(f"mem0 initialization failed: {str(e)}")
    
    async def validate_connection(self) -> bool:
        """Validate Redis connection health.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if not self._initialized:
            return False
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._redis_client.ping
            )
            return True
        except Exception as e:
            logger.warning(f"Redis connection validation failed: {e}")
            return False
    
    async def reconnect(self):
        """Attempt to reconnect to Redis and reinitialize mem0."""
        logger.info("Attempting to reconnect...")
        self._initialized = False
        
        try:
            await self.initialize()
            logger.info("Reconnection successful")
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            raise ConnectionError(f"Failed to reconnect: {str(e)}")
    
    def _ensure_initialized(self):
        """Ensure the manager is initialized before operations."""
        if not self._initialized:
            raise MemoryManagerError("MemoryManager not initialized. Call initialize() first.")
    
    def _validate_user_id(self, user_id: str):
        """Validate user ID format."""
        if not user_id or not isinstance(user_id, str):
            raise ValidationError("user_id must be a non-empty string")
        
        if len(user_id.strip()) == 0:
            raise ValidationError("user_id cannot be empty or whitespace")
    
    def _validate_content(self, content: str):
        """Validate memory content."""
        if not content or not isinstance(content, str):
            raise ValidationError("content must be a non-empty string")
        
        if len(content.strip()) == 0:
            raise ValidationError("content cannot be empty or whitespace")
        
        # Optional: Add content length limits
        max_content_length = 10000  # 10KB limit
        if len(content) > max_content_length:
            raise ValidationError(f"content exceeds maximum length of {max_content_length} characters")
    
    def _validate_metadata(self, metadata: Optional[Dict[str, Any]]):
        """Validate metadata structure."""
        if metadata is not None:
            if not isinstance(metadata, dict):
                raise ValidationError("metadata must be a dictionary")
            
            # Optional: Add metadata size limits
            import json
            try:
                metadata_str = json.dumps(metadata)
                max_metadata_size = 1000  # 1KB limit
                if len(metadata_str) > max_metadata_size:
                    raise ValidationError(f"metadata exceeds maximum size of {max_metadata_size} characters")
            except (TypeError, ValueError) as e:
                raise ValidationError(f"metadata must be JSON serializable: {str(e)}")  
  
    async def add_memory(self, content: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a new memory to the system.
        
        Args:
            content: The memory content to store
            user_id: User identifier for memory isolation
            metadata: Optional metadata to associate with the memory
            
        Returns:
            str: The memory identifier
            
        Raises:
            ValidationError: If input parameters are invalid
            ConnectionError: If Redis connection fails
            MemoryManagerError: If memory storage fails
        """
        self._ensure_initialized()
        
        # Validate inputs
        self._validate_content(content)
        self._validate_user_id(user_id)
        self._validate_metadata(metadata)
        
        # Check connection health
        if not await self.validate_connection():
            await self.reconnect()
        
        try:
            # Prepare memory data with user context
            memory_data = {
                "content": content.strip(),
                "user_id": user_id,
                "metadata": metadata or {}
            }
            
            # Add timestamp to metadata
            import datetime
            memory_data["metadata"]["timestamp"] = datetime.datetime.utcnow().isoformat()
            memory_data["metadata"]["source"] = "mcp_server"
            
            # Add memory using mem0
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self._memory.add(
                    messages=content,
                    user_id=user_id,
                    metadata=memory_data["metadata"]
                )
            )
            
            # Extract memory ID from result
            if isinstance(result, dict) and "id" in result:
                memory_id = result["id"]
            elif isinstance(result, list) and len(result) > 0 and "id" in result[0]:
                memory_id = result[0]["id"]
            else:
                # Fallback: generate a memory ID if not provided
                import uuid
                memory_id = str(uuid.uuid4())
                logger.warning(f"mem0 did not return memory ID, generated: {memory_id}")
            
            logger.info(f"Memory added successfully: {memory_id} for user {user_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to add memory for user {user_id}: {e}")
            
            # Check if it's a connection issue
            if not await self.validate_connection():
                raise ConnectionError(f"Redis connection lost during add operation: {str(e)}")
            
            raise MemoryManagerError(f"Failed to add memory: {str(e)}") 
   
    async def get_memories(self, query: str, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve memories based on query.
        
        Args:
            query: Search query for memories
            user_id: User identifier for memory isolation
            limit: Maximum number of results to return (default: 10)
            
        Returns:
            List[Dict[str, Any]]: List of memory records with metadata
            
        Raises:
            ValidationError: If input parameters are invalid
            ConnectionError: If Redis connection fails
            MemoryManagerError: If memory retrieval fails
        """
        self._ensure_initialized()
        
        # Validate inputs
        self._validate_user_id(user_id)
        
        if not query or not isinstance(query, str):
            raise ValidationError("query must be a non-empty string")
        
        if not isinstance(limit, int) or limit <= 0:
            raise ValidationError("limit must be a positive integer")
        
        # Enforce reasonable limit bounds
        max_limit = 100
        if limit > max_limit:
            limit = max_limit
            logger.warning(f"Limit capped at {max_limit}")
        
        # Check connection health
        if not await self.validate_connection():
            await self.reconnect()
        
        try:
            # Search memories using mem0
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._memory.search(
                    query=query.strip(),
                    user_id=user_id,
                    limit=limit
                )
            )
            
            # Process and format results
            formatted_results = []
            
            if isinstance(results, list):
                for result in results:
                    if isinstance(result, dict):
                        # Format memory record
                        memory_record = {
                            "id": result.get("id", "unknown"),
                            "content": result.get("memory", result.get("content", "")),
                            "user_id": user_id,
                            "metadata": result.get("metadata", {}),
                            "created_at": result.get("created_at", ""),
                            "relevance_score": result.get("score", 0.0)
                        }
                        formatted_results.append(memory_record)
            
            logger.info(f"Retrieved {len(formatted_results)} memories for user {user_id}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve memories for user {user_id}: {e}")
            
            # Check if it's a connection issue
            if not await self.validate_connection():
                raise ConnectionError(f"Redis connection lost during search operation: {str(e)}")
            
            # Return empty results for non-critical errors
            if "not found" in str(e).lower() or "no memories" in str(e).lower():
                logger.info(f"No memories found for query '{query}' and user {user_id}")
                return []
            
            raise MemoryManagerError(f"Failed to retrieve memories: {str(e)}")
    
    async def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """Delete a specific memory.
        
        Args:
            memory_id: Memory identifier to delete
            user_id: User identifier for memory isolation
            
        Returns:
            bool: True if memory was deleted successfully, False if not found
            
        Raises:
            ValidationError: If input parameters are invalid
            ConnectionError: If Redis connection fails
            MemoryManagerError: If memory deletion fails
        """
        self._ensure_initialized()
        
        # Validate inputs
        self._validate_user_id(user_id)
        
        if not memory_id or not isinstance(memory_id, str):
            raise ValidationError("memory_id must be a non-empty string")
        
        if len(memory_id.strip()) == 0:
            raise ValidationError("memory_id cannot be empty or whitespace")
        
        # Check connection health
        if not await self.validate_connection():
            await self.reconnect()
        
        try:
            # First, verify the memory exists and belongs to the user
            memory_exists = await self._verify_memory_ownership(memory_id, user_id)
            
            if not memory_exists:
                logger.info(f"Memory {memory_id} not found for user {user_id}")
                return False
            
            # Delete memory using mem0
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._memory.delete(memory_id=memory_id.strip())
            )
            
            # Check deletion result
            deletion_successful = True
            if isinstance(result, dict):
                deletion_successful = result.get("deleted", True)
            elif isinstance(result, bool):
                deletion_successful = result
            
            if deletion_successful:
                logger.info(f"Memory {memory_id} deleted successfully for user {user_id}")
                return True
            else:
                logger.warning(f"Memory {memory_id} deletion returned false for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id} for user {user_id}: {e}")
            
            # Check if it's a connection issue
            if not await self.validate_connection():
                raise ConnectionError(f"Redis connection lost during delete operation: {str(e)}")
            
            # Handle specific error cases
            if "not found" in str(e).lower():
                logger.info(f"Memory {memory_id} not found during deletion for user {user_id}")
                return False
            
            raise MemoryManagerError(f"Failed to delete memory: {str(e)}")
    
    async def _verify_memory_ownership(self, memory_id: str, user_id: str) -> bool:
        """Verify that a memory exists and belongs to the specified user.
        
        Args:
            memory_id: Memory identifier to verify
            user_id: User identifier to check ownership
            
        Returns:
            bool: True if memory exists and belongs to user, False otherwise
        """
        try:
            # Get all memories for the user and check if memory_id exists
            all_memories = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._memory.get_all(user_id=user_id)
            )
            
            if isinstance(all_memories, list):
                for memory in all_memories:
                    if isinstance(memory, dict) and memory.get("id") == memory_id:
                        return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Could not verify memory ownership for {memory_id}: {e}")
            # If we can't verify ownership, assume it exists to allow deletion attempt
            return True
