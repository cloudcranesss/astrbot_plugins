# AstrBot API 文档

本文档整理了 `astrbot.api` 模块中所有可用的公共API。

## 目录结构

```
astrbot/api/
├── __init__.py      # 核心功能导出
├── all.py           # 全部API统一导出
├── message_components.py  # 消息组件
├── event/           # 事件相关API
│   ├── __init__.py
│   └── filter/      # 事件过滤器
├── platform/        # 平台相关API
├── provider/        # LLM Provider相关API
├── star/            # 插件(Star)开发API
└── util/            # 工具类API
```

---

## 1. 核心模块 (`__init__.py`)

| 导出名称 | 类型 | 说明 |
|---------|------|------|
| `AstrBotConfig` | 类 | AstrBot配置管理类 |
| `BaseFunctionToolExecutor` | 类 | 函数工具执行器基类 |
| `FunctionTool` | 类 | LLM函数工具定义 |
| `ToolSet` | 类 | 工具集管理 |
| `agent` | 装饰器 | 注册Agent的装饰器 |
| `html_renderer` | 模块 | HTML渲染模块 |
| `llm_tool` | 装饰器 | 注册LLM工具的装饰器 |
| `logger` | 对象 | 日志记录器 |
| `sp` | 对象 | 服务提供商管理器 |

---

## 2. 全部API统一导出 (`all.py`)

### 2.1 配置
- `AstrBotConfig` - 配置管理

### 2.2 Event (事件)
| 名称 | 说明 |
|------|------|
| `MessageEventResult` | 消息事件结果 |
| `MessageChain` | 消息链 |
| `CommandResult` | 命令执行结果 |
| `EventResultType` | 事件结果类型枚举 |

### 2.3 Star (插件注册)
| 名称 | 说明 |
|------|------|
| `command` | 注册命令装饰器 |
| `command_group` | 注册命令组装饰器 |
| `event_message_type` | 注册事件消息类型装饰器 |
| `regex` | 注册正则匹配装饰器 |
| `platform_adapter_type` | 注册平台适配器类型装饰器 |
| `register` | 注册插件(Star)装饰器 |

### 2.4 Star 过滤器
| 名称 | 说明 |
|------|------|
| `EventMessageTypeFilter` | 事件消息类型过滤器 |
| `EventMessageType` | 事件消息类型枚举 |
| `PlatformAdapterTypeFilter` | 平台适配器类型过滤器 |
| `PlatformAdapterType` | 平台适配器类型枚举 |

### 2.5 Star 核心类
| 名称 | 说明 |
|------|------|
| `Context` | 插件上下文 |
| `Star` | 插件基类 |
| `StarTools` | 插件工具集 |

### 2.6 Provider (LLM提供商)
| 名称 | 说明 |
|------|------|
| `Provider` | LLM提供商基类 |
| `ProviderMetaData` | 提供商元数据 |
| `Personality` | 人格数据模型 |

### 2.7 Platform (平台)
| 名称 | 说明 |
|------|------|
| `AstrMessageEvent` | 消息事件抽象类 |
| `Platform` | 平台抽象类 |
| `AstrBotMessage` | 消息抽象类 |
| `MessageMember` | 消息成员 |
| `MessageType` | 消息类型枚举 |
| `PlatformMetadata` | 平台元数据 |
| `register_platform_adapter` | 注册平台适配器装饰器 |

---

## 3. 事件模块 (`event/`)

### 3.1 事件结果 (`event/__init__.py`)

| 名称 | 说明 |
|------|------|
| `AstrMessageEvent` | 消息事件抽象类 |
| `CommandResult` | 命令执行结果 |
| `EventResultType` | 事件结果类型枚举 |
| `MessageChain` | 消息链 |
| `MessageEventResult` | 消息事件结果 |
| `ResultContentType` | 结果内容类型枚举 |

### 3.2 事件过滤器 (`event/filter/`)

#### 装饰器
| 装饰器 | 说明 |
|--------|------|
| `after_message_sent` | 消息发送后回调 |
| `command` | 注册命令 |
| `command_group` | 注册命令组 |
| `custom_filter` | 注册自定义过滤器 |
| `event_message_type` | 注册事件消息类型 |
| `llm_tool` | 注册LLM工具 |
| `on_astrbot_loaded` | AstrBot加载完成回调 |
| `on_decorating_result` | 装饰结果回调 |
| `on_llm_request` | LLM请求回调 |
| `on_llm_response` | LLM响应回调 |
| `on_llm_tool_respond` | LLM工具响应回调 |
| `on_platform_loaded` | 平台加载完成回调 |
| `on_plugin_error` | 插件错误回调 |
| `on_plugin_loaded` | 插件加载回调 |
| `on_plugin_unloaded` | 插件卸载回调 |
| `on_using_llm_tool` | 使用LLM工具回调 |
| `on_waiting_llm_request` | 等待LLM请求回调 |
| `permission_type` | 注册权限类型 |
| `platform_adapter_type` | 注册平台适配器类型 |
| `regex` | 注册正则表达式匹配 |

#### 过滤器类
| 类名 | 说明 |
|------|------|
| `CustomFilter` | 自定义过滤器基类 |
| `EventMessageType` | 事件消息类型枚举 |
| `EventMessageTypeFilter` | 事件消息类型过滤器 |
| `PermissionType` | 权限类型枚举 |
| `PermissionTypeFilter` | 权限类型过滤器 |
| `PlatformAdapterType` | 平台适配器类型枚举 |
| `PlatformAdapterTypeFilter` | 平台适配器类型过滤器 |

---

## 4. 平台模块 (`platform/`)

| 名称 | 说明 |
|------|------|
| `AstrBotMessage` | 机器人消息抽象类 |
| `AstrMessageEvent` | 消息事件抽象类 |
| `Group` | 群组抽象类 |
| `MessageMember` | 消息成员抽象类 |
| `MessageType` | 消息类型枚举 |
| `Platform` | 平台抽象基类 |
| `PlatformMetadata` | 平台元数据 |
| `register_platform_adapter` | 注册平台适配器装饰器 |

---

## 5. Provider模块 (`provider/`)

| 名称 | 说明 |
|------|------|
| `LLMResponse` | LLM响应实体 |
| `Personality` | 人格数据模型 |
| `Provider` | LLM提供商基类 |
| `ProviderMetaData` | 提供商元数据 |
| `ProviderRequest` | 提供商请求实体 |
| `ProviderType` | 提供商类型枚举 |
| `STTProvider` | 语音转文字提供商基类 |

---

## 6. Star模块 (`star/`)

| 名称 | 说明 |
|------|------|
| `Context` | 插件上下文对象 |
| `Star` | 插件基类 |
| `StarTools` | 插件工具集 |
| `register` | 注册插件(Star)的装饰器 |

---

## 7. 工具模块 (`util/`)

| 名称 | 说明 |
|------|------|
| `SessionController` | 会话控制器 |
| `SessionWaiter` | 会话等待器 |
| `session_waiter` | 会话等待装饰器 |

---

## 8. 消息组件 (`message_components.py`)

从 `astrbot.core.message.components` 导出所有消息组件，包括但不限于：
- 文本消息
- 图片消息
- 表情消息
- @消息
- 引用消息
- 等等

---

## 使用示例

### 注册命令
```python
from astrbot import command

@command("hello")
async def hello(event, args):
    return "你好！"
```

### 创建插件
```python
from astrbot import register, Star

@register
class MyPlugin(Star):
    async def activate(self):
        # 插件激活时执行
        pass
    
    async def deactivate(self):
        # 插件停用时执行
        pass
```

### 使用LLM工具
```python
from astrbot import llm_tool

@llm_tool
async def search_tool(query: str) -> str:
    """搜索工具"""
    # 实现搜索逻辑
    return f"搜索结果: {query}"
```