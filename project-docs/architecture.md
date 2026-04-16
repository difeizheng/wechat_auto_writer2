# WeChat Auto Writer 技术架构设计

> **文档版本**：v1.0  
> **创建日期**：2026-04-16  
> **架构师**：AgentsOrchestrator

---

## 1. 系统架构概览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Streamlit Web 应用 (app.py)                        │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  文章生成页面 │  │  模板管理页面 │  │  历史记录页面 │  │   设置页面   │ │
│  │ (article_gen)│  │ (templates)  │  │  (history)   │  │  (settings)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           核心业务模块 (core/)                            │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    AI Writer (ai_writer.py)                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │
│  │  │ OpenAI      │  │ Claude      │  │ Ollama      │               │   │
│  │  │ Provider    │  │ Provider    │  │ Provider    │               │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │   │
│  │         └──────────────────────────────────────────┘             │   │
│  │                        AIProvider 抽象接口                         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌────────────────────────────┐  ┌────────────────────────────┐         │
│  │  WeChat API (wechat_api.py)│  │ Template Manager           │         │
│  │  - access_token 管理       │  │ (template_manager.py)      │         │
│  │  - 草稿上传                 │  │ - 模板 CRUD                │         │
│  │  - 素材管理                 │  │ - Prompt 构建              │         │
│  └────────────────────────────┘  └────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          数据持久层 (database/)                           │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────┐  ┌────────────────────────────┐         │
│  │  Database Manager          │  │  SQLite 数据库              │         │
│  │  (db_manager.py)           │  │  - articles 表              │         │
│  │  - CRUD 操作               │  │  - templates 表             │         │
│  │  - 事务管理                 │  │  - config 表                │         │
│  └────────────────────────────┘  └────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          外部服务接口                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ OpenAI API  │  │ Claude API  │  │ Ollama      │  │ 微信公众号   │     │
│  │             │  │             │  │ (本地)      │  │ API         │     │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 架构层次

| 层次 | 模块 | 负责内容 |
|------|------|----------|
| **表现层** | Streamlit UI | 用户交互、页面展示、状态管理 |
| **业务层** | core/ | AI生成、微信API、模板管理 |
| **数据层** | database/ | 数据持久化、缓存管理 |
| **外部服务** | 外部API | OpenAI/Claude/Ollama、微信公众号 |

---

## 2. 核心模块设计

### 2.1 AI Writer 模块

**设计原则**：抽象工厂模式，支持多模型切换

```python
# 核心接口设计
from abc import ABC, abstractmethod

class AIProvider(ABC):
    """AI提供商抽象接口"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> dict:
        """
        生成文章内容
        
        Args:
            prompt: 生成提示词
            **kwargs: 额外参数（temperature, max_tokens等）
        
        Returns:
            {
                "title": str,
                "content": str,  # HTML格式
                "digest": str,
                "keywords": list
            }
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查服务是否可用"""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """获取模型名称"""
        pass


class AIWriter:
    """AI文章生成器"""
    
    _providers = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "ollama": OllamaProvider
    }
    
    def __init__(self, model: str = "openai", settings: Settings):
        self.provider = self._get_provider(model, settings)
    
    def generate_article(
        self,
        topic: str,
        style: str = "科普",
        template: dict = None,
        word_count: int = 800
    ) -> dict:
        """生成公众号文章"""
        prompt = self._build_prompt(topic, style, template, word_count)
        return self.provider.generate(prompt)
    
    def switch_model(self, model: str) -> None:
        """切换AI模型"""
        self.provider = self._get_provider(model, self.settings)
```

**模型配置结构**：

```python
# OpenAI 配置
class OpenAIProvider(AIProvider):
    def __init__(self, settings: Settings):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = "gpt-4"  # 或 gpt-3.5-turbo

# Claude 配置
class ClaudeProvider(AIProvider):
    def __init__(self, settings: Settings):
        self.client = Anthropic(
            api_key=settings.CLAUDE_API_KEY
        )
        self.model = "claude-3-opus-20240229"

# Ollama 配置
class OllamaProvider(AIProvider):
    def __init__(self, settings: Settings):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = "llama2"  # 或其他本地模型
```

---

### 2.2 微信 API 模块

**设计原则**：Token缓存 + 自动刷新 + 错误重试

```python
class WeChatAPI:
    """微信公众号API封装"""
    
    BASE_URL = "https://api.weixin.qq.com/cgi-bin"
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token_cache = TokenCache()  # Token缓存器
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        获取access_token（自动缓存）
        
        缓存策略：
        - 本地文件缓存，有效期 7000秒（提前5分钟刷新）
        - 过期前自动刷新
        - 支持强制刷新
        """
        cached_token = self._token_cache.get()
        if cached_token and not force_refresh:
            return cached_token
        
        # 调用微信API获取新token
        url = f"{self.BASE_URL}/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret
        }
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            token = data["access_token"]
            expires_in = data["expires_in"]
            self._token_cache.set(token, expires_in)
            return token
        
        raise WeChatAPIError(f"获取token失败: {response.text}")
    
    def add_draft(self, articles: list) -> dict:
        """
        新增草稿到公众号
        
        Args:
            articles: 文章列表
                [{
                    "title": str,
                    "author": str,
                    "digest": str,
                    "content": str,  # HTML格式
                    "thumb_media_id": str,  # 封面图ID（可选）
                    "need_open_comment": int,
                    "only_fans_can_comment": int
                }]
        
        Returns:
            {"media_id": str}  # 草稿ID
        """
        token = self.get_access_token()
        url = f"{self.BASE_URL}/draft/add"
        data = {"articles": articles}
        
        response = requests.post(
            url,
            params={"access_token": token},
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            if "media_id" in result:
                return result
            raise WeChatAPIError(f"上传失败: {result.get('errmsg', '未知错误')}")
        
        raise WeChatAPIError(f"请求失败: {response.status_code}")
    
    def upload_image(self, image_path: str) -> dict:
        """
        上传图片素材
        
        Returns:
            {"media_id": str, "url": str}
        """
        token = self.get_access_token()
        url = f"{self.BASE_URL}/material/add_material"
        
        with open(image_path, "rb") as f:
            files = {"media": f}
            params = {
                "access_token": token,
                "type": "image"
            }
            response = requests.post(url, params=params, files=files)
        
        return response.json()
```

**Token缓存设计**：

```python
class TokenCache:
    """access_token缓存器"""
    
    CACHE_FILE = "data/token_cache.json"
    EXPIRE_MARGIN = 300  # 提前5分钟刷新
    
    def get(self) -> str | None:
        """获取缓存的token"""
        if not os.path.exists(self.CACHE_FILE):
            return None
        
        with open(self.CACHE_FILE, "r") as f:
            data = json.load(f)
        
        expires_at = data["expires_at"]
        if datetime.now() < expires_at - timedelta(seconds=self.EXPIRE_MARGIN):
            return data["token"]
        
        return None
    
    def set(self, token: str, expires_in: int) -> None:
        """保存token"""
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        data = {
            "token": token,
            "expires_at": expires_at.isoformat()
        }
        
        os.makedirs("data", exist_ok=True)
        with open(self.CACHE_FILE, "w") as f:
            json.dump(data, f)
```

---

### 2.3 数据库模块

**设计原则**：简单可靠，SQLite单文件，易于备份迁移

```python
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "data/wechat_writer.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建文章表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                digest TEXT,
                style TEXT,
                topic TEXT,
                template_id INTEGER,
                ai_model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                wechat_draft_id TEXT,
                wechat_media_id TEXT,
                status TEXT DEFAULT 'draft'
            )
        """)
        
        # 创建模板表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                prompt_template TEXT,
                style_config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # 创建配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    # CRUD 操作方法...
    def save_article(self, article: dict) -> int:
        """保存文章，返回ID"""
        pass
    
    def get_article(self, article_id: int) -> dict:
        """获取文章"""
        pass
    
    def list_articles(self, status: str = None, limit: int = 20) -> list:
        """列出文章"""
        pass
```

---

## 3. 数据流设计

### 3.1 文章生成流程

```
用户输入主题
      │
      ▼
┌─────────────────┐
│  选择AI模型     │  OpenAI / Claude / Ollama
│  选择文章风格   │  科普 / 故事 / 干货 / 互动
│  选择模板(可选) │
│  设置字数       │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  构建 Prompt    │  topic + style + template → prompt
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  AI 模型生成    │  调用对应Provider
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  解析响应       │  {title, content, digest, keywords}
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  实时预览       │  Markdown/HTML渲染
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  用户编辑       │  可修改内容
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  保存到数据库   │  status = 'draft'
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  上传到微信     │  调用WeChatAPI.add_draft()
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  更新状态       │  status = 'uploaded', wechat_draft_id
└─────────────────┘
```

### 3.2 草稿上传流程

```
准备上传
      │
      ▼
┌─────────────────┐
│  检查 access_token  │  缓存有效？
│     ↓ 有效：使用缓存
│     ↓ 无效：调用微信API获取
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  上传封面图(可选)   │  如有图片，先上传获取media_id
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  构造文章数据       │
│  {                 │
│    title,          │
│    author,         │
│    digest,         │
│    content (HTML), │
│    thumb_media_id  │
│  }                 │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  POST /draft/add   │  微信API
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  返回 media_id     │  草稿ID
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  更新数据库        │  wechat_draft_id, status='uploaded'
└─────────────────┘
      │
      ▼
✅ 用户可在公众号后台查看草稿
```

---

## 4. 技术决策记录

### 4.1 为什么选择 SQLite？

| 方面 | SQLite | PostgreSQL |
|------|--------|------------|
| **部署复杂度** | 无需安装，单文件 | 需要服务器进程 |
| **数据量** | 适合中小规模 | 适合大规模 |
| **备份迁移** | 复制文件即可 | 需要导出/导入 |
| **云端部署** | Streamlit Cloud可直接使用 | 需要外部数据库服务 |
| **开发效率** | 快速启动 | 配置复杂 |

**决策**：本项目数据量预计不大（文章、模板、配置），SQLite足够满足需求，且便于本地开发和Streamlit Cloud部署。

### 4.2 多模型切换实现

**方案**：抽象工厂模式 + 配置驱动

```python
# 配置中指定默认模型
DEFAULT_AI_MODEL: str = "openai"

# 运行时切换
writer = AIWriter(model="claude")  # 切换到Claude
writer.switch_model("ollama")      # 切换到Ollama
```

**优势**：
- 用户可在界面中实时切换模型
- 无需重启应用
- 易于添加新模型（实现AIProvider接口）

### 4.3 access_token缓存策略

**问题**：微信API限制每天获取token次数，频繁请求会触发限制

**解决方案**：
- 本地文件缓存（`data/token_cache.json`）
- 有效期7000秒，提前5分钟刷新
- 应用启动时检查缓存有效性
- 失败时自动重试一次

---

## 5. 安全设计要点

### 5.1 配置安全

| 要求 | 实现方式 |
|------|----------|
| API密钥不写入代码 | 使用 `.env` 文件 |
| 密钥不提交到Git | `.gitignore` 排除 `.env` |
| UI中密钥显示 | 密码框模式，隐藏显示 |
| 配置验证 | 启动时检查必需配置 |

### 5.2 输入验证

```python
def validate_topic(topic: str) -> tuple[bool, str]:
    """验证文章主题"""
    if not topic or len(topic.strip()) == 0:
        return False, "主题不能为空"
    if len(topic) > 200:
        return False, "主题长度不能超过200字符"
    if contains_malicious_content(topic):
        return False, "主题包含不合规内容"
    return True, ""

def validate_content(content: str) -> tuple[bool, str]:
    """验证文章内容"""
    if len(content) < 100:
        return False, "内容过短，至少需要100字"
    if len(content) > 50000:
        return False, "内容过长，不能超过50000字"
    return True, ""
```

### 5.3 错误处理

- 不在UI中暴露API密钥
- 不显示详细的内部错误堆栈
- 提供用户友好的中文错误提示
- 记录详细日志到本地文件（开发调试用）

---

## 6. 扩展性设计

### 6.1 未来可扩展方向

| 功能 | 当前状态 | 扩展方案 |
|------|----------|----------|
| **更多AI模型** | 3个模型 | 实现新的AIProvider |
| **图片生成** | 不支持 | 添加AI图片生成模块 |
| **多公众号** | 单公众号 | 添加公众号管理表 |
| **定时发布** | 不支持 | 添加定时任务模块 |
| **数据分析** | 不支持 | 添加统计模块 |
| **批量生成** | 不支持 | 添加批量处理功能 |

### 6.2 模块扩展接口

```python
# 新增AI模型只需实现接口
class NewAIProvider(AIProvider):
    def generate(self, prompt: str, **kwargs) -> dict:
        # 实现生成逻辑
        pass
    
    def is_available(self) -> bool:
        # 检查可用性
        pass

# 注册到AIWriter
AIWriter._providers["new_model"] = NewAIProvider
```

---

## 7. 部署架构

### 7.1 本地部署

```
用户电脑
    │
    ├── Python 3.10+
    ├── Streamlit
    ├── SQLite 数据库文件
    ├── .env 配置文件
    └── 外部API访问
```

### 7.2 Streamlit Cloud部署

```
Streamlit Cloud
    │
    ├── 应用容器（免费）
    ├── SQLite 数据库（容器内）
    ├── secrets.toml 配置（替代.env）
    └── 外部API访问
```

**注意**：Streamlit Cloud 不支持 `.env`，需要使用 `secrets.toml`：

```toml
# .streamlit/secrets.toml
OPENAI_API_KEY = "sk-xxx"
CLAUDE_API_KEY = "xxx"
WECHAT_APP_ID = "xxx"
WECHAT_APP_SECRET = "xxx"
```

---

## 8. 依赖关系图

```
app.py
    │
    ├── config/settings.py
    │       └── python-dotenv
    │
    ├── core/ai_writer.py
    │       ├── openai
    │       ├── anthropic
    │       └── requests (ollama)
    │
    ├── core/wechat_api.py
    │       └── requests
    │       └── TokenCache
    │
    ├── core/template_manager.py
    │       └── database/db_manager.py
    │
    ├── database/db_manager.py
    │       └── sqlite3 (内置)
    │
    └── ui/pages/
            └── streamlit
            └── markdown (渲染)
```

---

## 9. 性能考虑

| 方面 | 优化策略 |
|------|----------|
| **AI调用延迟** | 显示生成进度，异步处理（可选） |
| **Token缓存** | 减少微信API调用，避免触发限制 |
| **数据库查询** | 使用索引，分页查询 |
| **大文章渲染** | 限制预览长度，分块显示 |
| **并发请求** | Streamlit自带会话管理 |

---

**架构设计完成！**

此架构设计为开发团队提供了清晰的技术蓝图，后续开发将按此架构进行模块实现。