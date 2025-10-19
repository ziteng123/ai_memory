from mem0 import Memory

config = {
    "vector_store": {
        "provider": "redis",
        "config": {
            "collection_name": "mem0",
            "embedding_model_dims": 768,
            "redis_url": "redis://localhost:6379"
        }
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "gemma3:270m-it-fp16",
            "temperature": 0,
            "max_tokens": 2000,
            "ollama_base_url": "http://localhost:11434",  # Ensure this URL is correct
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:latest",
            # Alternatively, you can use "snowflake-arctic-embed:latest"
            "ollama_base_url": "http://localhost:11434",
        },
    },
}

# Initialize Memory with the configuration
m = Memory.from_config(config)

# Add a memory
m.add("I have lots of money and I want to buy a big house.", user_id="Jerry")

# Retrieve memories
memories = m.get_all(user_id="Jerry")
print(memories)
# result = m.search(query="Where are you doing?", user_id="john")
# print(result)