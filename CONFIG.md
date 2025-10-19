# Memory MCP Server Configuration

This document describes the configuration options for the Memory MCP Server.

## Configuration Files

The server looks for configuration files in the following order:

1. File specified with `-c/--config` command line option
2. `config.json` in the current directory
3. `memory_mcp_config.json` in the current directory
4. `~/.memory_mcp/config.json` in the user's home directory
5. `/etc/memory_mcp/config.json` system-wide configuration

If no configuration file is found, the server uses default settings.

## Example Configuration Files

- `config.example.json` - Basic example configuration
- `config.development.json` - Development environment with debug logging
- `config.production.json` - Production environment with external services

## Configuration Structure

### Redis Configuration

```json
{
  "redis": {
    "url": "redis://localhost:6379",
    "collection_name": "mcp_memories",
    "db": 0
  }
}
```

**Options:**
- `url` (required): Redis connection URL
  - Format: `redis://[username:password@]host:port[/database]`
  - Examples:
    - `redis://localhost:6379` (local Redis)
    - `redis://user:pass@redis-server:6379/0` (authenticated)
    - `rediss://redis-server:6380` (SSL/TLS connection)
- `collection_name` (required): Name for the memory collection in Redis
- `db` (optional): Redis database number (default: 0)

### mem0 Configuration

```json
{
  "mem0": {
    "llm": {
      "provider": "ollama",
      "config": {
        "model": "llama3.2:3b",
        "temperature": 0.1,
        "max_tokens": 1000,
        "base_url": "http://localhost:11434"
      }
    },
    "embedder": {
      "provider": "ollama",
      "config": {
        "model": "nomic-embed-text:latest",
        "base_url": "http://localhost:11434"
      }
    },
    "vector_store": {
      "provider": "redis",
      "config": {
        "collection_name": "mcp_memories",
        "embedding_model_dims": 768
      }
    }
  }
}
```

**LLM Configuration:**
- `provider` (required): LLM provider name (e.g., "ollama", "openai")
- `config` (required): Provider-specific configuration
  - `model`: Model name to use
  - `temperature`: Sampling temperature (0.0-1.0)
  - `max_tokens`: Maximum tokens in response
  - `base_url`: API endpoint URL (for Ollama)

**Embedder Configuration:**
- `provider` (required): Embedding provider name
- `config` (required): Provider-specific configuration
  - `model`: Embedding model name
  - `base_url`: API endpoint URL (for Ollama)

**Vector Store Configuration:**
- `provider` (required): Vector store provider ("redis")
- `config` (required): Vector store configuration
  - `collection_name`: Collection name in vector store
  - `embedding_model_dims`: Embedding vector dimensions

### Server Configuration

```json
{
  "server": {
    "name": "memory-mcp",
    "version": "1.0.0",
    "log_level": "INFO"
  }
}
```

**Options:**
- `name` (required): Server name for MCP protocol
- `version` (required): Server version
- `log_level` (optional): Logging level
  - Values: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
  - Default: "INFO"

## Environment Variable Overrides

Configuration values can be overridden using environment variables:

| Environment Variable | Configuration Path | Example |
|---------------------|-------------------|---------|
| `REDIS_URL` | `redis.url` | `redis://localhost:6379` |
| `REDIS_DB` | `redis.db` | `1` |
| `REDIS_COLLECTION` | `redis.collection_name` | `my_memories` |
| `MCP_SERVER_NAME` | `server.name` | `my-memory-server` |
| `MCP_LOG_LEVEL` | `server.log_level` | `DEBUG` |
| `OLLAMA_MODEL` | `mem0.llm.config.model` | `llama3.2:1b` |
| `OLLAMA_EMBED_MODEL` | `mem0.embedder.config.model` | `nomic-embed-text` |

Example:
```bash
export REDIS_URL="redis://my-redis:6379"
export MCP_LOG_LEVEL="DEBUG"
python main.py
```

## Configuration Validation

Use the built-in validation to check your configuration:

```bash
# Validate a configuration file
python main.py --validate-config config.json

# Create a sample configuration file
python main.py --create-config
```

## Common Configuration Scenarios

### Local Development

```json
{
  "redis": {
    "url": "redis://localhost:6379",
    "collection_name": "mcp_memories_dev",
    "db": 1
  },
  "server": {
    "log_level": "DEBUG"
  }
}
```

### Docker Compose

```json
{
  "redis": {
    "url": "redis://redis:6379",
    "collection_name": "mcp_memories"
  },
  "mem0": {
    "llm": {
      "config": {
        "base_url": "http://ollama:11434"
      }
    },
    "embedder": {
      "config": {
        "base_url": "http://ollama:11434"
      }
    }
  }
}
```

### Production with Authentication

```json
{
  "redis": {
    "url": "rediss://username:password@redis-cluster:6380/0",
    "collection_name": "mcp_memories_prod"
  },
  "server": {
    "log_level": "WARNING"
  }
}
```

## Troubleshooting

### Redis Connection Issues

1. **Connection refused**: Check if Redis is running and accessible
2. **Authentication failed**: Verify username/password in Redis URL
3. **Database not found**: Ensure the database number exists in Redis

### mem0 Configuration Issues

1. **Model not found**: Ensure the specified model is available in Ollama
2. **Connection timeout**: Check if Ollama server is running and accessible
3. **Embedding dimension mismatch**: Verify embedding model dimensions

### Common Error Messages

- `Redis URL is required`: Missing or empty Redis URL in configuration
- `mem0 LLM configuration is required`: Missing LLM configuration section
- `Configuration validation failed`: Invalid configuration structure
- `Failed to connect to Redis`: Redis server not accessible

## Security Considerations

1. **Redis Authentication**: Use authentication for production Redis instances
2. **SSL/TLS**: Use `rediss://` URLs for encrypted Redis connections
3. **Network Security**: Restrict network access to Redis and Ollama services
4. **Configuration Files**: Protect configuration files containing credentials
5. **Environment Variables**: Use environment variables for sensitive values

## Performance Tuning

1. **Redis Configuration**: Tune Redis memory settings for your workload
2. **Connection Pooling**: Redis client uses connection pooling automatically
3. **Embedding Dimensions**: Match embedding dimensions to your model
4. **Collection Names**: Use separate collections for different environments