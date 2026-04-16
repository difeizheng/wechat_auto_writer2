# WeChat Auto Writer 开发任务列表

> **项目名称**：WeChat Auto Writer - 公众号文章智能写作助手  
> **规范文档**：project-specs/wechat-auto-writer-setup.md  
> **创建日期**：2026-04-16  
> **任务版本**：v1.0

---

## 📋 项目需求概要

| 需求项 | 确认选择 | 说明 |
|--------|----------|------|
| **AI模型** | 多模型支持 | OpenAI GPT / Claude / Ollama 本地模型，可切换 |
| **微信API** | 已有权限 | AppID 和 AppSecret 已就绪 |
| **部署方式** | 本地 + 云端 | Streamlit Cloud 双支持 |
| **功能优先级** | 1→2→3→4 | 生成 → 上传 → 模板 → 历史 |
| **界面语言** | 中文 | 全中文界面 |

---

## 🎯 开发阶段概览

| Phase | 阶段名称 | 任务数 | 预计工作量 | 依赖关系 |
|-------|----------|--------|------------|----------|
| Phase 1 | 基础架构搭建 | 6 | 中等 | 无 |
| Phase 2 | 核心模块开发 | 5 | 复杂 | Phase 1 |
| Phase 3 | UI界面开发 | 5 | 中等 | Phase 1, 2 |
| Phase 4 | 功能完善与测试 | 4 | 简单 | Phase 1-3 |
| **总计** | - | **20个任务** | **约12-15人日** | - |

---

## Phase 1: 基础架构搭建

> **目标**：建立项目骨架、配置管理、数据库基础

### [ ] Task 1.1: 项目结构搭建

**描述**：创建完整的项目目录结构，初始化Python项目

**负责Agent**：Senior Developer

**工作量**：简单

**文件清单**：
```
wechat_auto_writer2/
├── app.py                    # Streamlit主入口（空文件占位）
├── requirements.txt          # Python依赖
├── config/
│   ├── __init__.py
│   ├── settings.py          # 配置管理（空文件占位）
│   └── .env.example         # 环境变量模板
├── core/
│   ├── __init__.py
│   ├── ai_writer.py         # AI生成引擎（空文件占位）
│   ├── wechat_api.py        # 微信API封装（空文件占位）
│   └── template_manager.py  # 模板管理（空文件占位）
├── database/
│   ├── __init__.py
│   ├── models.py            # 数据模型（空文件占位）
│   └── db_manager.py        # 数据库操作（空文件占位）
├── ui/
│   ├── __init__.py
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── article_gen.py
│   │   ├── templates.py
│   │   ├── history.py
│   │   └── settings.py
│   └── components/
│       └── __init__.py
├── utils/
│   ├── __init__.py
│   ├── helpers.py
│   └── validators.py
└── assets/
    └── .gitkeep
```

**验收标准**：
- [ ] 所有目录和文件已创建
- [ ] `requirements.txt` 包含所有必要依赖
- [ ] `.gitignore` 已配置（忽略.env、__pycache__、*.db等）

**参考规范**：第三章 3.1 模块划分

---

### [ ] Task 1.2: 配置管理模块

**描述**：实现环境变量加载、配置读取、多环境支持

**负责Agent**：Senior Developer

**工作量**：简单

**文件清单**：
- `config/settings.py` - 配置管理类
- `config/.env.example` - 环境变量模板

**功能要求**：
1. 从 `.env` 文件加载配置
2. 提供配置访问接口
3. 支持必需配置项验证
4. 敏感信息不写入代码

**配置项定义**：
```python
# config/settings.py 核心结构
class Settings:
    # AI模型配置
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    CLAUDE_API_KEY: str
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_AI_MODEL: str = "openai"  # openai/claude/ollama
    
    # 微信公众号配置
    WECHAT_APP_ID: str
    WECHAT_APP_SECRET: str
    
    # 应用配置
    DATABASE_PATH: str = "data/wechat_writer.db"
    DEBUG_MODE: bool = False
```

**验收标准**：
- [ ] `Settings` 类可正确加载 `.env` 配置
- [ ] 必需配置缺失时抛出明确错误
- [ ] `.env.example` 包含所有配置项说明

**参考规范**：第二章 2.2 依赖、第八章 8.1 API密钥管理

---

### [ ] Task 1.3: 数据库模型定义

**描述**：定义SQLite数据模型，创建表结构

**负责Agent**：Senior Developer

**工作量**：简单

**文件清单**：
- `database/models.py` - 数据模型定义

**数据表设计**：
```python
# articles 表 - 文章记录
{
    "id": INTEGER PRIMARY KEY,
    "title": TEXT NOT NULL,
    "content": TEXT,
    "digest": TEXT,              # 摘要
    "style": TEXT,               # 风格
    "topic": TEXT,               # 主题
    "template_id": INTEGER,      # 关联模板
    "ai_model": TEXT,            # 使用的AI模型
    "created_at": DATETIME,
    "updated_at": DATETIME,
    "wechat_draft_id": TEXT,     # 微信草稿ID
    "wechat_media_id": TEXT,     # 微信素材ID
    "status": TEXT               # draft/uploaded/published
}

# templates 表 - 文章模板
{
    "id": INTEGER PRIMARY KEY,
    "name": TEXT NOT NULL,
    "category": TEXT,
    "prompt_template": TEXT,     # Prompt模板
    "style_config": TEXT,        # 风格配置JSON
    "created_at": DATETIME,
    "is_active": BOOLEAN
}

# config 表 - 系统配置
{
    "key": TEXT PRIMARY KEY,
    "value": TEXT,
    "updated_at": DATETIME
}
```

**验收标准**：
- [ ] 三个表的模型定义完整
- [ ] 使用 SQLAlchemy 或原生 sqlite3 实现
- [ ] 包含默认模板初始化数据

**参考规范**：第六章 6.1 表结构

---

### [ ] Task 1.4: 数据库管理模块

**描述**：实现数据库连接、CRUD操作、事务管理

**负责Agent**：Senior Developer

**工作量**：中等

**文件清单**：
- `database/db_manager.py` - 数据库操作封装

**功能要求**：
1. 数据库初始化（创建表、插入默认数据）
2. 文章 CRUD 操作
3. 模板 CRUD 操作
4. 配置读写操作
5. 数据库备份/恢复功能

**核心方法**：
```python
class DatabaseManager:
    def init_db() -> None
    def save_article(article: dict) -> int
    def get_article(article_id: int) -> dict
    def list_articles(status: str = None) -> list
    def update_article(article_id: int, data: dict) -> bool
    def delete_article(article_id: int) -> bool
    
    def save_template(template: dict) -> int
    def get_template(template_id: int) -> dict
    def list_templates(category: str = None) -> list
    def update_template(template_id: int, data: dict) -> bool
    def delete_template(template_id: int) -> bool
    
    def get_config(key: str) -> str
    def set_config(key: str, value: str) -> bool
```

**验收标准**：
- [ ] 数据库文件自动创建
- [ ] 所有 CRUD 方法正常工作
- [ ] 异常处理完善
- [ ] 支持上下文管理器

**参考规范**：第六章 数据库设计

---

### [ ] Task 1.5: 工具函数模块

**描述**：实现通用工具函数和数据验证器

**负责Agent**：Junior Developer

**工作量**：简单

**文件清单**：
- `utils/helpers.py` - 工具函数
- `utils/validators.py` - 数据验证

**功能要求**：
```python
# utils/helpers.py
def format_datetime(dt: datetime) -> str      # 时间格式化
def truncate_text(text: str, length: int) -> str  # 文本截断
def generate_unique_id() -> str                # 唯一ID生成
def safe_filename(name: str) -> str            # 安全文件名
def html_to_plain(html: str) -> str            # HTML转纯文本
def plain_to_html(text: str) -> str            # 纯文本转HTML

# utils/validators.py
def validate_topic(topic: str) -> tuple[bool, str]   # 验证主题
def validate_content(content: str) -> tuple[bool, str]  # 验证内容
def validate_config(config: dict) -> tuple[bool, str]  # 验证配置
```

**验收标准**：
- [ ] 所有函数有单元测试
- [ ] 边界情况处理完善
- [ ] 函数文档完整

**参考规范**：第七章 8.3 用户输入验证

---

### [ ] Task 1.6: Streamlit 主入口搭建

**描述**：创建 Streamlit 主应用入口，配置页面导航

**负责Agent**：UI Developer

**工作量**：简单

**文件清单**：
- `app.py` - Streamlit 主入口

**功能要求**：
1. 侧边栏导航（文章生成、模板管理、历史记录、设置）
2. 页面状态管理
3. 初始化数据库
4. 加载配置
5. 中文界面设置

**核心结构**：
```python
import streamlit as st
from config.settings import Settings
from database.db_manager import DatabaseManager

def main():
    st.set_page_config(
        page_title="公众号文章智能写作助手",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 初始化
    init_database()
    load_settings()
    
    # 侧边栏导航
    with st.sidebar:
        page = st.radio(
            "功能导航",
            ["📝 文章生成", "📋 模板管理", "📚 历史记录", "⚙️ 设置"],
            label_visibility="collapsed"
        )
    
    # 页面路由
    if page == "📝 文章生成":
        show_article_generation()
    elif page == "📋 模板管理":
        show_template_management()
    # ...
```

**验收标准**：
- [ ] `streamlit run app.py` 可启动应用
- [ ] 中文显示正常
- [ ] 导航切换流畅
- [ ] 数据库初始化正确

**参考规范**：第七章 7.1 页面结构

---

## Phase 2: 核心模块开发

> **目标**：实现AI文章生成和微信API集成（优先级最高的功能）

### [ ] Task 2.1: AI 模型抽象层（多模型支持）

**描述**：实现统一AI接口，支持 OpenAI/Claude/Ollama 三种模型

**负责Agent**：Senior Developer

**工作量**：复杂

**文件清单**：
- `core/ai_writer.py` - AI生成引擎

**功能要求**：
1. 统一的 AI 接口抽象
2. OpenAI GPT 集成
3. Claude 集成
4. Ollama 本地模型集成
5. 模型切换机制
6. 错误重试机制

**核心接口设计**：
```python
from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> dict:
        """生成文章，返回 {title, content, digest, keywords}"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查模型是否可用"""
        pass

class OpenAIProvider(AIProvider):
    """OpenAI GPT 实现"""
    pass

class ClaudeProvider(AIProvider):
    """Claude 实现"""
    pass

class OllamaProvider(AIProvider):
    """Ollama 本地模型实现"""
    pass

class AIWriter:
    def __init__(self, model: str = "openai"):
        self.provider = self._get_provider(model)
    
    def generate_article(
        self, 
        topic: str, 
        style: str = "科普",
        template: dict = None,
        word_count: int = 800
    ) -> dict:
        """生成公众号文章"""
        pass
```

**验收标准**：
- [ ] 三种模型均可正常调用
- [ ] 统一返回格式
- [ ] 模型切换无需重启应用
- [ ] API 调用失败有明确错误提示

**参考规范**：第五章 5.1 支持的AI模型、第五章 5.2 文章生成流程

---

### [ ] Task 2.2: Prompt 模板系统

**描述**：设计文章生成的 Prompt 模板，支持多种风格

**负责Agent**：Senior Developer

**工作量**：中等

**文件清单**：
- `core/ai_writer.py` 扩展 - Prompt 构建模块

**功能要求**：
1. 默认 Prompt 模板（科普、故事、干货、互动等风格）
2. 支持自定义模板
3. Prompt 变量替换
4. 输出格式约束

**Prompt 模板示例**：
```
你是一位专业的公众号文章写手。
请根据以下要求创作一篇公众号文章：

主题：{topic}
风格：{style}
字数：约{word_count}字

结构要求：
- 吸引人的开头
- 清晰的小标题分段
- 重点加粗或列表呈现
- 引导互动的结尾

请严格按以下格式输出：
【标题】...
【摘要】（50字以内）...
【正文】（HTML格式）...
【关键词】...
```

**验收标准**：
- [ ] 至少支持 4 种预设风格
- [ ] 输出格式解析正确
- [ ] 支持模板变量注入

**参考规范**：第五章 5.3 Prompt模板设计

---

### [ ] Task 2.3: 微信公众号 API 封装

**描述**：实现微信公众号 API 完整封装

**负责Agent**：Senior Developer

**工作量**：复杂

**文件清单**：
- `core/wechat_api.py` - 微信API封装

**功能要求**：
1. access_token 获取与缓存
2. 草稿箱管理（新增、列表、删除）
3. 素材上传（图片）
4. 错误处理与重试
5. 调用频率限制

**核心方法设计**：
```python
class WeChatAPI:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token = None
        self._token_expires_at = None
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """获取access_token，自动缓存和刷新"""
        pass
    
    def add_draft(self, articles: list) -> dict:
        """
        新增草稿
        articles: [{"title", "author", "digest", "content", ...}]
        返回: {"media_id": "..."}
        """
        pass
    
    def upload_image(self, image_path: str) -> dict:
        """上传图片素材，返回media_id"""
        pass
    
    def get_draft_list(self, offset: int = 0, count: int = 10) -> list:
        """获取草稿列表"""
        pass
    
    def delete_draft(self, media_id: str) -> bool:
        """删除草稿"""
        pass
```

**验收标准**：
- [ ] access_token 自动缓存，2小时内有效
- [ ] 草稿上传功能正常
- [ ] 图片上传功能正常
- [ ] 错误信息明确友好
- [ ] 符合微信API调用规范

**参考规范**：第四章 微信公众号API集成要点

---

### [ ] Task 2.4: 模板管理器

**描述**：实现文章模板的创建、编辑、应用功能

**负责Agent**：Junior Developer

**工作量**：中等

**文件清单**：
- `core/template_manager.py` - 模板管理器

**功能要求**：
1. 模板 CRUD 操作
2. 模板分类管理
3. 模板应用（注入 Prompt）
4. 默认模板初始化

**核心方法**：
```python
class TemplateManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_template(
        self, 
        name: str, 
        category: str,
        prompt_template: str,
        style_config: dict
    ) -> int:
        """创建模板"""
        pass
    
    def get_template(self, template_id: int) -> dict:
        """获取模板"""
        pass
    
    def list_templates(self, category: str = None) -> list:
        """列出模板"""
        pass
    
    def apply_template(
        self, 
        template_id: int, 
        variables: dict
    ) -> str:
        """应用模板，返回填充后的Prompt"""
        pass
    
    def init_default_templates(self) -> None:
        """初始化默认模板"""
        pass
```

**验收标准**：
- [ ] 默认模板至少 3 个
- [ ] 模板变量替换正确
- [ ] 模板可正常增删改查

**参考规范**：第三章 3.1 模块划分

---

### [ ] Task 2.5: 核心模块集成测试

**描述**：编写核心模块的集成测试

**负责Agent**：QA Engineer

**工作量**：中等

**文件清单**：
- `tests/test_ai_writer.py`
- `tests/test_wechat_api.py`
- `tests/test_template_manager.py`

**测试覆盖**：
1. AI 生成功能（Mock API 响应）
2. 微信 API 调用（Mock 响应）
3. 模板管理
4. 数据库操作

**验收标准**：
- [ ] 测试覆盖率 > 70%
- [ ] 所有测试通过
- [ ] 异常情况有测试用例

---

## Phase 3: UI界面开发

> **目标**：按优先级实现UI页面（生成 → 上传 → 模板 → 历史）

### [ ] Task 3.1: 文章生成页面（最高优先级）

**描述**：实现文章生成核心页面，支持主题输入、模板选择、AI配置、实时预览

**负责Agent**：UI Developer

**工作量**：复杂

**文件清单**：
- `ui/pages/article_gen.py` - 文章生成页面

**页面布局**：
```
[侧边栏]
├── 选择AI模型（OpenAI/Claude/Ollama）
├── 选择文章风格（科普/故事/干货/互动）
├── 选择模板（可选）
├── 字数设置（500-2000）
└── 上传封面图（可选）

[主区域]
├── 输入框：文章主题/关键词
├── [生成文章] 按钮
├── 实时预览区（Markdown渲染）
├── 编辑区（可修改内容）
├── [保存草稿] [上传到微信] 按钮
└── 上传状态反馈
```

**功能要求**：
1. 多模型切换（下拉选择）
2. 风格选择
3. 模板选择
4. 实时预览（Markdown/HTML渲染）
5. 内容编辑
6. 生成进度显示
7. 保存到本地数据库
8. 上传到微信草稿箱

**验收标准**：
- [ ] 页面布局清晰美观
- [ ] 生成功能正常工作
- [ ] 预览显示正确
- [ ] 保存功能正常
- [ ] 上传功能正常（需微信API）

**参考规范**：第七章 7.2 文章生成页面核心流程

---

### [ ] Task 3.2: 草稿上传功能（第二优先级）

**描述**：集成微信API，实现一键上传到公众号草稿箱

**负责Agent**：Senior Developer

**工作量**：中等

**文件清单**：
- `ui/pages/article_gen.py` 扩展 - 上传功能
- `ui/components/upload_status.py` - 上传状态组件

**功能要求**：
1. 上传前内容验证
2. 图片素材上传（可选）
3. 草稿箱上传
4. 上传进度显示
5. 成功/失败反馈
6. 草稿链接返回

**验收标准**：
- [ ] 上传成功返回草稿ID
- [ ] 失败有明确错误提示
- [ ] 可在公众号后台看到草稿

**参考规范**：第四章 4.3 草稿上传流程

---

### [ ] Task 3.3: 模板管理页面（第三优先级）

**描述**：实现模板创建、编辑、分类管理

**负责Agent**：UI Developer

**工作量**：中等

**文件清单**：
- `ui/pages/templates.py` - 模板管理页面

**页面功能**：
1. 模板列表展示（卡片或表格）
2. 创建新模板
3. 编辑现有模板
4. 删除模板
5. 模板分类筛选
6. 模板预览

**验收标准**：
- [ ] CRUD 功能完整
- [ ] 界面友好易用
- [ ] 中文界面

**参考规范**：第七章 7.1 页面结构

---

### [ ] Task 3.4: 历史记录页面（第四优先级）

**描述**：展示已生成文章列表，支持查看、编辑、重新上传

**负责Agent**：UI Developer

**工作量**：中等

**文件清单**：
- `ui/pages/history.py` - 历史记录页面

**页面功能**：
1. 文章列表（分页）
2. 搜索过滤
3. 文章详情查看
4. 编辑文章
5. 重新上传到微信
6. 删除记录
7. 状态标识（草稿/已上传/已发布）

**验收标准**：
- [ ] 列表展示清晰
- [ ] 编辑功能正常
- [ ] 重新上传功能正常
- [ ] 分页正常

**参考规范**：第七章 7.1 页面结构

---

### [ ] Task 3.5: 设置页面

**描述**：API密钥配置、公众号配置、模型选择

**负责Agent**：UI Developer

**工作量**：简单

**文件清单**：
- `ui/pages/settings.py` - 设置页面

**页面功能**：
1. AI 模型配置
   - OpenAI API Key 输入
   - Claude API Key 输入
   - Ollama 地址配置
   - 默认模型选择
2. 微信公众号配置
   - AppID 输入
   - AppSecret 输入
   - 连接测试
3. 应用设置
   - 数据库路径
   - 调试模式

**验收标准**：
- [ ] 配置保存正确
- [ ] 敏感信息显示为密码框
- [ ] 连接测试功能正常

**参考规范**：第七章 7.1 页面结构

---

## Phase 4: 功能完善与测试

> **目标**：完善细节、测试、文档

### [ ] Task 4.1: 错误处理与用户反馈

**描述**：完善全局错误处理、用户友好的错误提示

**负责Agent**：Senior Developer

**工作量**：简单

**文件清单**：
- `utils/error_handler.py` - 错误处理模块
- 各模块错误处理完善

**功能要求**：
1. 全局异常捕获
2. 友好错误提示（中文）
3. 日志记录
4. 错误恢复建议

**验收标准**：
- [ ] 所有异常有友好提示
- [ ] 错误日志记录完整
- [ ] 不暴露敏感信息

**参考规范**：第八章 安全性要求

---

### [ ] Task 4.2: access_token 缓存机制

**描述**：实现微信 access_token 的智能缓存和自动刷新

**负责Agent**：Senior Developer

**工作量**：简单

**文件清单**：
- `core/wechat_api.py` 扩展
- `utils/token_cache.py` - Token缓存工具

**功能要求**：
1. 本地缓存（文件或数据库）
2. 过期前自动刷新
3. 并发请求保护
4. 缓存失效处理

**验收标准**：
- [ ] Token 缓存有效
- [ ] 自动刷新正常
- [ ] 不频繁请求微信API

**参考规范**：第四章 4.4 注意事项、第八章 8.2 access_token缓存

---

### [ ] Task 4.3: 端到端测试

**描述**：完整功能测试，确保所有流程正常工作

**负责Agent**：QA Engineer

**工作量**：中等

**文件清单**：
- `tests/e2e/` - 端到端测试目录

**测试场景**：
1. 完整生成流程：主题输入 → 生成 → 预览 → 保存
2. 上传流程：生成 → 上传 → 验证
3. 模板流程：创建模板 → 应用模板 → 生成文章
4. 历史流程：生成多篇文章 → 搜索 → 编辑
5. 配置流程：修改配置 → 保存 → 验证生效

**验收标准**：
- [ ] 所有核心流程测试通过
- [ ] 测试报告完整
- [ ] 发现的问题已修复

**参考规范**：第十一章 验收标准

---

### [ ] Task 4.4: 文档与部署准备

**描述**：编写 README、使用指南、部署说明

**负责Agent**：Technical Writer

**工作量**：简单

**文件清单**：
- `README.md` - 项目说明
- `docs/QUICKSTART.md` - 快速开始指南
- `docs/DEPLOYMENT.md` - 部署指南

**文档内容**：
1. 项目介绍
2. 功能特性
3. 安装步骤
4. 配置说明
5. 使用指南
6. 常见问题
7. 部署说明（本地/Streamlit Cloud）

**验收标准**：
- [ ] 文档完整清晰
- [ ] 新用户可按文档运行
- [ ] 包含截图示例

---

## 📊 任务统计

### 按阶段统计
| Phase | 任务数 | 预计工作量 |
|-------|--------|------------|
| Phase 1: 基础架构 | 6 | 中等 (2-3人日) |
| Phase 2: 核心模块 | 5 | 复杂 (4-5人日) |
| Phase 3: UI界面 | 5 | 中等 (3-4人日) |
| Phase 4: 完善测试 | 4 | 简单 (2-3人日) |
| **总计** | **20** | **约12-15人日** |

### 按负责Agent统计
| Agent类型 | 任务数 | 主要任务 |
|-----------|--------|----------|
| Senior Developer | 7 | 核心架构、AI模型、微信API |
| UI Developer | 4 | 所有UI页面 |
| Junior Developer | 2 | 工具函数、模板管理器 |
| QA Engineer | 2 | 测试用例 |
| Technical Writer | 1 | 文档编写 |

### 按优先级统计（功能）
| 优先级 | 功能 | 相关任务 | 状态 |
|--------|------|----------|------|
| 1 (最高) | 文章生成 | Task 2.1, 2.2, 3.1 | 核心功能 |
| 2 | 草稿上传 | Task 2.3, 3.2 | 核心功能 |
| 3 | 模板管理 | Task 2.4, 3.3 | 扩展功能 |
| 4 (最低) | 历史记录 | Task 3.4 | 辅助功能 |

---

## 🚀 开发建议

### 开发顺序
```
Phase 1 (基础架构)
    ↓
Phase 2.1-2.3 (AI生成 + 微信API) ← 核心功能优先
    ↓
Phase 3.1-3.2 (文章生成 + 上传页面) ← 最高优先级功能
    ↓
Phase 2.4 + Phase 3.3 (模板管理) ← 第三优先级
    ↓
Phase 3.4 (历史记录) ← 第四优先级
    ↓
Phase 3.5 + Phase 4 (完善与测试)
```

### 风险提示
1. **微信API限制**：每日调用次数有限，开发时注意缓存
2. **AI模型成本**：OpenAI/Claude 有调用成本，建议开发时多用 Ollama
3. **配置安全**：`.env` 文件不要提交到版本控制
4. **中文编码**：确保数据库和文件编码正确处理中文

### 里程碑
- **Milestone 1**：Phase 1 完成，可启动应用框架
- **Milestone 2**：Task 2.1-2.3 完成，核心模块可用
- **Milestone 3**：Phase 3.1-3.2 完成，核心功能可用（生成+上传）
- **Milestone 4**：Phase 3 完成，全部功能可用
- **Milestone 5**：Phase 4 完成，可交付

---

**任务列表创建完成！**

**创建日期**：2026-04-16  
**任务版本**：v1.0  
**状态**：待开发