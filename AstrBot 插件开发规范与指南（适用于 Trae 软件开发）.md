# AstrBot 插件开发规范与指南（适用于 Trae 软件开发）

基于官方文档整理的 **AstrBot 插件开发完整规范**，可直接用于 AI 编程助手（如 Trae）生成代码。

---

## 📋 一、项目初始化规范

### 1.1 目录结构
```
astrbot_plugin_xxx/
├── main.py              # 必须：插件入口文件
├── metadata.yaml        # 必须：插件元数据
├── _conf_schema.json    # 可选：配置 Schema
├── requirements.txt     # 可选：依赖列表
├── logo.png             # 可选：256x256 图标
└── ...其他模块文件
```

### 1.2 metadata.yaml 模板
```yaml
name: astrbot_plugin_xxx
version: 1.0.0
author: 作者名
description: 插件描述
repo: https://github.com/用户名/仓库名
display_name: 展示名称（可选）
```

### 1.3 命名规范
- **仓库名**：`astrbot_plugin_` 前缀 + 全小写 + 无空格
- **类名**：继承 `Star` 类，建议与插件名对应
- **文件名**：入口必须为 `main.py`

---

## 💻 二、核心代码模板

### 2.1 最小插件实例
```python
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("helloworld", "author", "描述", "1.0.0", "repo_url")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令"""
        user_name = event.get_sender_name()
        logger.info("触发指令!")
        yield event.plain_result(f"Hello, {user_name}!")
    
    async def terminate(self):
        """插件卸载时调用（可选）"""
        pass
```

---

## 🎯 三、消息处理规范

### 3.1 指令注册方式

| 类型       | 装饰器                                                 | 示例                                                |
| ---------- | ------------------------------------------------------ | --------------------------------------------------- |
| 普通指令   | `@filter.command("cmd")`                               | `/helloworld`                                       |
| 带参指令   | `@filter.command("add")`                               | `/add 1 2` → `def add(self, event, a: int, b: int)` |
| 指令组     | `@filter.command_group("math")`                        | `/math add 1 2`                                     |
| 指令别名   | `@filter.command("help", alias={'帮助', 'helpme'})`    | 多个触发词                                          |
| 管理员指令 | `@filter.permission_type(filter.PermissionType.ADMIN)` | 仅管理员可用                                        |

### 3.2 事件过滤器组合
```python
@filter.command("helloworld")
@filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE)
@filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
async def helloworld(self, event: AstrMessageEvent):
    yield event.plain_result("私聊 QQ 消息触发!")
```

### 3.3 事件钩子（Hooks）
```python
# Bot 加载完成
@filter.on_astrbot_loaded()
async def on_loaded(self):
    print("AstrBot 初始化完成")

# LLM 请求前（可修改 prompt）
@filter.on_llm_request()
async def on_llm_req(self, event: AstrMessageEvent, req: ProviderRequest):
    req.system_prompt += "自定义提示"

# LLM 响应后
@filter.on_llm_response()
async def on_llm_resp(self, event: AstrMessageEvent, resp: LLMResponse):
    print(resp.completion_text)

# 发送消息前装饰
@filter.on_decorating_result()
async def on_decorate(self, event: AstrMessageEvent):
    result = event.get_result()
    result.chain.append(Comp.Plain("!"))

# 停止事件传播
event.stop_event()  # 阻止后续插件/LLM 处理
```

---

## 📤 四、消息发送规范

### 4.1 被动回复（yield）
```python
yield event.plain_result("文本消息")
yield event.image_result("https://example.com/img.jpg")  # URL
yield event.image_result("/path/to/local.jpg")  # 本地路径
yield event.chain_result([Comp.Plain("文本"), Comp.Image.fromURL("url")])
```

### 4.2 主动推送（定时任务等）
```python
# 保存会话标识
umo = event.unified_msg_origin

# 后续任意位置发送
from astrbot.api.event import MessageChain
chain = MessageChain().message("主动消息").file_image("img.jpg")
await self.context.send_message(umo, chain)
```

### 4.3 富媒体消息组件
```python
import astrbot.api.message_components as Comp

chain = [
    Comp.At(qq=event.get_sender_id()),  # @某人
    Comp.Plain("文本"),
    Comp.Image.fromURL("https://..."),  # 网络图片
    Comp.Image.fromFileSystem("/path/to/img.jpg"),  # 本地图片
    Comp.Record(file="voice.wav"),  # 语音（wav 格式）
    Comp.Video.fromURL("https://..."),  # 视频
    Comp.File(file="/path/to/file.pdf", name="file.pdf"),  # 文件
]
yield event.chain_result(chain)
```

### 4.4 群合并转发（OneBot v11）
```python
from astrbot.api.message_components import Node, Plain, Image

node = Node(
    uin=905617992,
    name="发送者名",
    content=[Plain("hi"), Image.fromFileSystem("test.jpg")]
)
yield event.chain_result([node])
```

---

## ⚙️ 五、插件配置规范

### 5.1 _conf_schema.json 模板
```json
{
  "token": {
    "type": "string",
    "description": "API Token",
    "hint": "请输入你的 API 密钥",
    "obvious_hint": true
  },
  "timeout": {
    "type": "int",
    "description": "超时时间",
    "default": 30,
    "hint": "单位：秒"
  },
  "mode": {
    "type": "string",
    "description": "运行模式",
    "options": ["chat", "agent", "workflow"],
    "default": "chat"
  },
  "nested_config": {
    "type": "object",
    "description": "嵌套配置",
    "items": {
      "sub_key": {
        "type": "string",
        "default": "value"
      }
    }
  },
  "provider_select": {
    "type": "string",
    "_special": "select_provider",
    "description": "选择模型提供商"
  },
  "uploaded_files": {
    "type": "file",
    "description": "上传文件",
    "file_types": ["pdf", "docx"],
    "default": []
  }
}
```

### 5.2 在代码中使用配置
```python
from astrbot.api import AstrBotConfig

@register("config_plugin", "author", "配置示例", "1.0.0")
class ConfigPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        
        # 读取配置
        token = self.config.get("token", "")
        timeout = self.config.get("timeout", 30)
        
        # 修改并保存配置
        self.config["new_key"] = "value"
        self.config.save_config()
```

---

## 🤖 六、AI 功能集成规范

### 6.1 调用 LLM
```python
# 获取当前会话的模型 ID
provider_id = await self.context.get_current_chat_provider_id(umo=event.unified_msg_origin)

# 调用模型
llm_resp = await self.context.llm_generate(
    chat_provider_id=provider_id,
    prompt="你好，世界！"
)
print(llm_resp.completion_text)
```

### 6.2 定义 Tool（函数调用）
#### 方式一：装饰器（推荐）
```python
@filter.llm_tool(name="get_weather")
async def get_weather(self, event: AstrMessageEvent, location: str) -> MessageEventResult:
    """获取天气信息。
    Args:
        location(string): 地点名称
    """
    resp = await self.fetch_weather(location)
    yield event.plain_result(f"天气：{resp}")
```

#### 方式二：dataclass 定义
```python
from pydantic import Field
from pydantic.dataclasses import dataclass
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext

@dataclass
class BilibiliTool(FunctionTool[AstrAgentContext]):
    name: str = "bilibili_videos"
    description: str = "搜索 B 站视频"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "keywords": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["keywords"]
        }
    )
    
    async def call(self, context, **kwargs) -> ToolExecResult:
        return f"视频：{kwargs['keywords']}"

# 注册 Tool
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.context.add_llm_tools(BilibiliTool())
```

### 6.3 调用 Agent（工具循环）
```python
from astrbot.core.agent.tool import ToolSet

llm_resp = await self.context.tool_loop_agent(
    event=event,
    chat_provider_id=provider_id,
    prompt="搜索 B 站上关于 AstrBot 的视频",
    tools=ToolSet([BilibiliTool()]),
    max_steps=30,
    tool_call_timeout=60
)
print(llm_resp.completion_text)
```

### 6.4 多智能体（Multi-Agent）
```python
# 将子 Agent 定义为 Tool
@dataclass
class SubAgent1(FunctionTool[AstrAgentContext]):
    name: str = "weather_agent"
    description: str = "天气查询子智能体"
    parameters: dict = Field(...)
    
    async def call(self, context, **kwargs) -> ToolExecResult:
        ctx = context.context.context
        event = context.context.event
        prov_id = await ctx.get_current_chat_provider_id(event.unified_msg_origin)
        
        llm_resp = await ctx.tool_loop_agent(
            event=event,
            chat_provider_id=prov_id,
            prompt=kwargs["query"],
            tools=ToolSet([WeatherTool()]),
            max_steps=30
        )
        return llm_resp.completion_text

# 主 Agent 调用
@filter.command("test")
async def test(self, event: AstrMessageEvent):
    prov_id = await self.context.get_current_chat_provider_id(event.unified_msg_origin)
    llm_resp = await self.context.tool_loop_agent(
        event=event,
        chat_provider_id=prov_id,
        prompt="查询北京天气",
        system_prompt="你是主智能体，负责分配任务给子智能体",
        tools=ToolSet([SubAgent1(), AssignAgentTool()]),
        max_steps=30
    )
    yield event.plain_result(llm_resp.completion_text)
```

### 6.5 对话管理
```python
from astrbot.core.conversation_mgr import ConversationManager
from astrbot.core.agent.message import UserMessageSegment, AssistantMessageSegment, TextPart

conv_mgr = self.context.conversation_manager
curr_cid = await conv_mgr.get_curr_conversation_id(event.unified_msg_origin)

# 获取对话历史
conversation = await conv_mgr.get_conversation(event.unified_msg_origin, curr_cid)

# 添加对话记录
user_msg = UserMessageSegment(content=[TextPart(text="用户消息")])
assistant_msg = AssistantMessageSegment(content=[TextPart(text="AI 回复")])
await conv_mgr.add_message_pair(
    cid=curr_cid,
    user_message=user_msg,
    assistant_message=assistant_msg
)

# 新建/切换/删除对话
new_cid = await conv_mgr.new_conversation(event.unified_msg_origin, title="新对话")
await conv_mgr.switch_conversation(event.unified_msg_origin, new_cid)
await conv_mgr.delete_conversation(event.unified_msg_origin, curr_cid)
```

### 6.6 人格管理
```python
persona_mgr = self.context.persona_manager

# 获取人格
persona = await persona_mgr.get_persona("persona_id")
all_personas = await persona_mgr.get_all_personas()

# 创建人格
new_persona = await persona_mgr.create_persona(
    persona_id="my_persona",
    system_prompt="你是一个助手",
    begin_dialogs=["你好", "你好！有什么可以帮你？"],
    tools=["tool1", "tool2"]  # None=全部，[]=禁用
)

# 更新/删除人格
await persona_mgr.update_persona("my_persona", system_prompt="新的提示词")
await persona_mgr.delete_persona("my_persona")
```

---

## 💾 七、数据存储规范

### 7.1 KV 存储（简单数据）
```python
# 存
await self.put_kv_data("key", value)

# 取
value = await self.get_kv_data("key", default_value)

# 删
await self.delete_kv_data("key")
```

### 7.2 大文件存储
```python
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

# 获取插件数据目录
plugin_data_path = get_astrbot_data_path() / "plugin_data" / self.name

# 保存文件
file_path = plugin_data_path / "data.json"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(data)
```

> ⚠️ **重要**：禁止将持久化数据存储在插件自身目录，必须使用 `data/plugin_data/{plugin_name}/`

---

## 🖼️ 八、文转图规范

### 8.1 基础用法
```python
@filter.command("image")
async def on_image(self, event: AstrMessageEvent, text: str):
    url = await self.text_to_image(text)  # 返回 URL
    # path = await self.text_to_image(text, return_url=False)  # 返回本地路径
    yield event.image_result(url)
```

### 8.2 自定义 HTML 模板（Jinja2）
```python
TMPL = '''
<div style="font-size: 32px;">
    <h1 style="color: black;">Todo List</h1>
    <ul>
    {% for item in items %}
        <li>{{ item }}</li>
    {% endfor %}
    </ul>
</div>
'''

@filter.command("todo")
async def todo_list(self, event: AstrMessageEvent):
    options = {
        "type": "png",
        "quality": 90,
        "full_page": True,
        "omit_background": True  # 透明背景
    }
    url = await self.html_render(
        TMPL, 
        {"items": ["吃饭", "睡觉", "玩原神"]},
        options=options
    )
    yield event.image_result(url)
```

---

## 🔁 九、会话控制规范

### 9.1 基础会话控制器
```python
from astrbot.core.utils.session_waiter import session_waiter, SessionController
import astrbot.api.message_components as Comp

@filter.command("成语接龙")
async def start_idiom_game(self, event: AstrMessageEvent):
    yield event.plain_result("请发送一个成语~")
    
    @session_waiter(timeout=60, record_history_chains=False)
    async def idiom_waiter(controller: SessionController, event: AstrMessageEvent):
        idiom = event.message_str
        
        if idiom == "退出":
            await event.send(event.plain_result("已退出~"))
            controller.stop()
            return
        
        if len(idiom) != 4:
            await event.send(event.plain_result("必须是四字成语~"))
            return  # 不中断会话，继续等待
        
        # 回复
        result = event.make_result()
        result.chain = [Comp.Plain("先见之明")]
        await event.send(result)
        
        # 重置超时
        controller.keep(timeout=60, reset_timeout=True)
    
    try:
        await idiom_waiter(event)
    except TimeoutError:
        yield event.plain_result("超时了！")
    except Exception as e:
        yield event.plain_result(f"错误：{e}")
    finally:
        event.stop_event()  # 阻止事件继续传播
```

### 9.2 自定义会话 ID（群组会话）
```python
from astrbot.core.utils.session_waiter import SessionFilter

class GroupFilter(SessionFilter):
    def filter(self, event: AstrMessageEvent) -> str:
        # 以群组 ID 作为会话标识
        return event.get_group_id() if event.get_group_id() else event.unified_msg_origin

@filter.command("组队游戏")
async def start_group_game(self, event: AstrMessageEvent):
    await group_waiter(event, session_filter=GroupFilter())
```

---

## 🔧 十、高级功能与杂项

### 10.1 获取平台实例
```python
from astrbot.api.platform import AiocqhttpAdapter

platform = self.context.get_platform(filter.PlatformAdapterType.AIOCQHTTP)
assert isinstance(platform, AiocqhttpAdapter)
# 调用底层 API
client = platform.get_client()
await client.api.call_action("delete_msg", message_id=123)
```

### 10.2 调用协议端 API（QQ 为例）
```python
if event.get_platform_name() == "aiocqhttp":
    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
    assert isinstance(event, AiocqhttpMessageEvent)
    
    client = event.bot
    ret = await client.api.call_action('delete_msg', message_id=event.message_obj.message_id)
    logger.info(f"删除消息结果：{ret}")
```

### 10.3 获取已加载的插件/平台
```python
# 获取所有插件
plugins = self.context.get_all_stars()  # List[StarMetadata]

# 获取所有平台
from astrbot.api.platform import Platform
platforms = self.context.platform_manager.get_insts()  # List[Platform]
```

---

## ✅ 十一、开发最佳实践

| 类别         | 规范要求                                       |
| ------------ | ---------------------------------------------- |
| **代码质量** | 使用 `ruff` 格式化；添加完整注释；功能需测试   |
| **异步编程** | 禁止使用 `requests`，必须用 `aiohttp`/`httpx`  |
| **异常处理** | 每个 Handler 必须有 try-except，避免插件崩溃   |
| **数据存储** | 持久化数据存 `data/plugin_data/{plugin_name}/` |
| **依赖管理** | 必须提供 `requirements.txt`                    |
| **热重载**   | 修改代码后在 WebUI 点击"重载插件"无需重启      |
| **生态贡献** | 优先给现有插件提 PR，而非重复造轮子            |

---

## 🚀 十二、调试流程

1. **克隆项目**
   ```bash
   git clone https://github.com/AstrBotDevs/AstrBot
   mkdir -p AstrBot/data/plugins
   cd AstrBot/data/plugins
   git clone <你的插件仓库>
   ```

2. **启动 AstrBot**
   ```bash
   cd ../../
   python main.py  # 或使用 Docker/启动器
   ```

3. **热重载**
   - 修改插件代码
   - 访问 WebUI → 插件管理 → 找到插件 → `...` → `重载插件`

4. **查看日志**
   - 使用 `logger.info()` 输出调试信息
   - 查看控制台或日志文件
