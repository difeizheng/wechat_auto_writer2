# 项目规范：微信公众号文章自动生成与上传系统

## 零、用户需求确认 ✅

| 需求项 | 用户选择 | 说明 |
|--------|----------|------|
| **AI模型** | D - 多模型支持 | 支持 OpenAI GPT / Claude / Ollama 本地模型，可切换 |
| **微信API** | A - 已有开发者权限 | 已有 AppID 和 AppSecret，可直接对接 |
| **部署方式** | A + B | 本地运行 + Streamlit Cloud 云端部署双支持 |
| **功能优先级** | 1,2,3,4 | 文章生成 → 草稿上传 → 模板管理 → 历史记录 |
| **界面语言** | A - 中文 | 全中文界面，符合公众号用户习惯 |

**开发重点**：优先完成核心功能链路（生成→上传），再扩展模板和历史管理。

---

## 一、项目概述

### 1.1 项目名称
WeChat Auto Writer - 公众号文章智能写作助手

### 1.2 项目目标
开发一个基于Streamlit的Web应用，实现：
- AI自动生成公众号文章内容
- 自动上传到微信公众号草稿箱
- 提供友好的交互界面管理写作流程

### 1.3 核心功能
1. **文章生成**：通过AI（支持多种模型）生成公众号文章
2. **模板管理**：支持文章模板创建、编辑、应用
3. **草稿上传**：通过微信公众号API上传到草稿箱
4. **历史管理**：保存已生成文章，支持查看、编辑、重新上传
5. **配置管理**：管理API密钥、公众号配置等

---

## 二、技术栈

### 2.1 核心技术
| 技术 | 用途 |
|------|------|
| **Python 3.10+** | 主要开发语言 |
| **Streamlit** | Web前端界面 |
| **微信公众号API** | 草稿箱上传、素材管理 |
| **AI API** | 文章内容生成（支持OpenAI、Claude、本地模型） |
| **SQLite** | 本地数据存储（文章、模板、配置） |

### 2.2 Python依赖
```
streamlit>=1.28.0
requests>=2.31.0
openai>=1.0.0  # 或其他AI SDK
python-dotenv>=1.0.0
sqlite3 (内置)
pillow>=10.0.0  # 图片处理（可选）
```

---

## 三、系统架构

### 3.1 模块划分
```
wechat_auto_writer2/
├── app.py                 # Streamlit主入口
├── config/
│   ├── settings.py        # 配置管理
│   └── .env.example       # 环境变量模板
├── core/
│   ├── ai_writer.py       # AI文章生成引擎
│   ├── wechat_api.py      # 微信公众号API封装
│   ├── template_manager.py # 模板管理
├── database/
│   ├── models.py          # 数据模型
│   ├── db_manager.py      # 数据库操作
├── ui/
│   ├── pages/
│   │   ├── article_gen.py # 文章生成页面
│   │   ├── templates.py   # 模板管理页面
│   │   ├── history.py     # 历史文章页面
│   │   ├── settings.py    # 设置页面
│   ├── components/        # 可复用UI组件
├── utils/
│   ├── helpers.py         # 工具函数
│   ├── validators.py      # 数据验证
└── assets/                # 静态资源（模板图片等）
```

### 3.2 数据流
```
用户输入主题/模板
    ↓
AI Writer生成文章
    ↓
用户预览/编辑
    ↓
WeChat API上传草稿
    ↓
返回草稿ID/链接
```

---

## 四、微信公众号API集成要点

### 4.1 必需配置
- **AppID**：公众号开发者ID
- **AppSecret**：公众号开发者密码
- **access_token**：通过API获取，2小时有效期

### 4.2 核心API接口
| 功能 | API接口 | 说明 |
|------|---------|------|
| 获取access_token | `/cgi-bin/token` | 每日调用次数有限，需缓存 |
| 新增草稿 | `/cgi-bin/draft/add` | 上传文章到草稿箱 |
| 上传图文素材 | `/cgi-bin/material/add_news` | 上传永久素材 |
| 上传图片 | `/cgi-bin/material/add_material` | 上传封面图等 |

### 4.3 草稿上传流程
```python
# 1. 获取access_token
# 2. 构造文章数据结构
articles = [{
    "title": "标题",
    "author": "作者",
    "digest": "摘要",
    "content": "HTML内容",
    "thumb_media_id": "封面图素材ID",  # 可选
    "need_open_comment": 0,
    "only_fans_can_comment": 0
}]
# 3. 调用draft/add接口
# 4. 返回media_id（草稿ID）
```

### 4.4 注意事项
- content必须是HTML格式
- 图片需先上传为素材获取media_id
- access_token需要缓存，避免频繁请求
- 接口调用有每日限制

---

## 五、AI文章生成模块

### 5.1 支持的AI模型
| 模型 | API | 特点 |
|------|-----|------|
| OpenAI GPT | openai SDK | 通用性强 |
| Claude | Anthropic SDK | 写作质量高 |
| 本地模型 | Ollama | 无需付费，隐私性好 |

### 5.2 文章生成流程
```python
def generate_article(topic, template, style):
    prompt = build_prompt(topic, template, style)
    response = ai_client.generate(prompt)
    article = parse_response(response)
    return {
        "title": article.title,
        "content": article.html_content,
        "digest": article.summary,
        "tags": article.keywords
    }
```

### 5.3 Prompt模板设计
```
你是一位专业的公众号文章写手。
请根据以下要求创作一篇公众号文章：

主题：{topic}
风格：{style}（如：科普、故事、干货、互动）
字数：约{word_count}字
结构要求：
- 吸引人的开头
- 清晰的小标题分段
- 重点加粗或列表呈现
- 引导互动的结尾

请输出：
标题：...
摘要（50字）：...
正文（HTML格式）：...
关键词：...
```

---

## 六、数据库设计

### 6.1 表结构
```sql
-- 文章表
CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    digest TEXT,
    style TEXT,
    topic TEXT,
    template_id INTEGER,
    ai_model TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    wechat_draft_id TEXT,  -- 草稿ID
    wechat_media_id TEXT,  -- 素材ID
    status TEXT DEFAULT 'draft'  -- draft/uploaded/published
);

-- 模板表
CREATE TABLE templates (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    prompt_template TEXT,
    style_config TEXT,
    created_at DATETIME,
    is_active BOOLEAN DEFAULT 1
);

-- 配置表
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME
);
```

---

## 七、UI界面设计

### 7.1 页面结构
| 页面 | 功能 |
|------|------|
| **首页** | 快速生成文章、状态概览 |
| **文章生成** | 主题输入、模板选择、AI配置、实时预览 |
| **模板管理** | 创建/编辑模板、模板分类 |
| **历史记录** | 已生成文章列表、编辑、上传状态 |
| **设置** | API密钥配置、公众号配置、模型选择 |

### 7.2 文章生成页面核心流程
```
[侧边栏]
├── 选择AI模型
├── 选择文章风格
├── 选择模板（可选）
├── 字数设置
└── 上传封面图（可选）

[主区域]
├── 输入文章主题/关键词
├── [生成文章] 按钮
├── 实时预览区（Markdown渲染）
├── 编辑区（可修改内容）
├── [上传到草稿箱] 按钮
└── 上传状态反馈
```

---

## 八、安全性要求

### 8.1 API密钥管理
- 使用`.env`文件存储敏感配置
- 不将密钥写入代码或数据库明文
- 提供`.env.example`模板

### 8.2 access_token缓存
- 本地缓存，避免频繁请求
- 自动刷新机制（临近过期时刷新）
- 失败重试机制

### 8.3 用户输入验证
- 主题长度限制
- 内容格式验证
- 防止恶意内容

---

## 九、部署建议

### 9.1 本地运行
```bash
streamlit run app.py
```

### 9.2 可选部署方式
| 方式 | 适用场景 |
|------|----------|
| 本地运行 | 个人使用 |
| Streamlit Cloud | 免费、简单部署 |
| Docker + 云服务器 | 稳定、可控 |
| 内网部署 | 企业内部使用 |

---

## 十、交付要求

### 10.1 必须交付
1. 完整的Streamlit应用代码
2. AI文章生成功能正常工作
3. 微信公众号草稿上传功能正常工作
4. 模板管理功能
5. 基本的配置管理界面
6. 项目文档（README）

### 10.2 可选增强
- 图片上传与处理
- 多公众号管理
- 定时发布功能
- 文章数据分析
- 批量生成功能

---

## 十一、验收标准

### 11.1 功能验收
- [ ] 能成功生成一篇完整的公众号文章
- [ ] 能成功上传到微信公众号草稿箱
- [ ] 能管理文章模板
- [ ] 能查看历史生成的文章
- [ ] 配置能正确保存和使用

### 11.2 代码质量
- 代码结构清晰，模块化良好
- 关键功能有注释说明
- 异常处理完善
- 无明显的安全漏洞

---

**文档版本**：v1.0
**创建日期**：2026-04-16
**项目类型**：Python + Streamlit + 微信API集成