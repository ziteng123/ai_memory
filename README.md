# Memory MCP Server

一个基于 Model Context Protocol (MCP) 的智能内存管理服务器，使用 mem0 库和 Redis 作为后端存储，为 AI 应用提供持久化记忆能力。

## 项目描述

Memory MCP Server 是一个专业的内存管理解决方案，通过 MCP 协议为 AI 应用提供智能记忆存储、检索和管理功能。它结合了 mem0 的先进记忆管理能力和 Redis 的高性能存储，支持多用户隔离、语义搜索和灵活的元数据管理。

## 功能特点

### 🧠 智能记忆管理
- **语义存储**: 使用向量嵌入技术存储和索引记忆内容
- **智能检索**: 基于语义相似度的记忆搜索和排序
- **用户隔离**: 支持多用户环境下的记忆数据隔离
- **元数据支持**: 灵活的元数据存储和查询功能

### 🔧 技术架构
- **MCP 协议**: 标准化的模型上下文协议接口
- **mem0 集成**: 先进的记忆管理和向量化处理
- **Redis 后端**: 高性能的数据存储和向量数据库
- **异步处理**: 基于 asyncio 的高并发处理能力

### 🛡️ 可靠性保障
- **错误处理**: 完善的错误分类和处理机制
- **连接管理**: 自动重连和连接健康检查
- **配置验证**: 严格的配置文件验证和环境变量支持
- **日志记录**: 结构化日志和操作审计

### ⚙️ 配置灵活性
- **多配置源**: 支持配置文件、环境变量等多种配置方式
- **环境适配**: 开发、测试、生产环境配置模板
- **动态配置**: 支持配置热重载和验证

## 使用方式

### 环境要求

- Python 3.8+
- Redis 服务器
- Ollama (用于本地 LLM 和嵌入模型)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd memory-mcp-server
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **启动 Redis 服务**
```bash
# 使用 Docker
docker run -d --name redis -p 6379:6379 redis:latest

# 或使用系统包管理器安装
# macOS: brew install redis && brew services start redis
# Ubuntu: sudo apt install redis-server && sudo systemctl start redis
```

4. **启动 Ollama 服务**
```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 拉取所需模型
ollama pull llama3.2:3b
ollama pull nomic-embed-text:latest
```

### 配置服务器

1. **创建配置文件**
```bash
python main.py --create-config
```

2. **编辑配置文件** (`config.json`)
```json
{
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
  },
  "server": {
    "name": "memory-mcp",
    "version": "1.0.0",
    "log_level": "INFO"
  }
}
```

### 启动服务器

```bash
# 使用默认配置
python main.py

# 使用自定义配置文件
python main.py -c config.json

# 启用调试日志
python main.py --log-level DEBUG

# 验证配置文件
python main.py --validate-config config.json
```

### MCP 工具使用

服务器提供以下 MCP 工具：

#### 1. 添加记忆 (`add_memory`)
```json
{
  "name": "add_memory",
  "arguments": {
    "content": "用户喜欢喝咖啡，特别是拿铁",
    "user_id": "user123",
    "metadata": {
      "category": "preference",
      "source": "conversation"
    }
  }
}
```

#### 2. 检索记忆 (`get_memory`)
```json
{
  "name": "get_memory",
  "arguments": {
    "query": "用户的饮品偏好",
    "user_id": "user123",
    "limit": 5
  }
}
```

#### 3. 删除记忆 (`delete_memory`)
```json
{
  "name": "delete_memory",
  "arguments": {
    "memory_id": "memory_id_here",
    "user_id": "user123"
  }
}
```

## 开发步骤

### 开发环境设置

1. **创建虚拟环境**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows
```

2. **安装开发依赖**
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio black flake8 mypy
```

3. **设置开发配置**
```bash
cp config.development.json config.json
# 编辑 config.json 以匹配您的开发环境
```

### 代码结构

```
memory-mcp-server/
├── main.py                 # 主入口点和命令行接口
├── memory_mcp_server.py    # MCP 服务器核心实现
├── memory_manager.py       # 记忆管理逻辑
├── config_manager.py       # 配置管理和验证
├── error_handler.py        # 错误处理和日志
├── run_server.py          # 简化的启动脚本
├── requirements.txt       # Python 依赖
├── CONFIG.md             # 详细配置文档
└── config.*.json         # 配置文件模板
```

### 开发工作流

1. **代码格式化**
```bash
black *.py
```

2. **代码检查**
```bash
flake8 *.py
mypy *.py
```

3. **运行测试**
```bash
pytest
```

4. **本地测试**
```bash
# 启动开发服务器
python main.py -c config.development.json --log-level DEBUG
```

### 扩展开发

#### 添加新的 MCP 工具
1. 在 `MemoryMCPServer._register_tools()` 中注册新工具
2. 实现对应的处理方法
3. 添加输入验证和错误处理
4. 更新文档和测试

#### 自定义记忆管理逻辑
1. 扩展 `MemoryManager` 类
2. 添加新的记忆操作方法
3. 实现相应的验证和错误处理
4. 更新配置选项

#### 集成其他向量数据库
1. 在 `config_manager.py` 中添加新的配置选项
2. 在 `memory_manager.py` 中实现新的后端支持
3. 更新配置验证逻辑

### 部署建议

#### Docker 部署
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

#### 生产环境配置
- 使用 Redis Cluster 或 Redis Sentinel 提高可用性
- 配置适当的日志级别和日志轮转
- 设置环境变量覆盖敏感配置
- 使用进程管理器（如 systemd 或 supervisor）

### 监控和维护

- 监控 Redis 连接状态和性能指标
- 定期检查记忆数据的存储使用情况
- 监控 Ollama 服务的响应时间和可用性
- 设置适当的告警和日志分析

---

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 支持

如有问题或需要帮助，请创建 GitHub Issue 或联系维护者。