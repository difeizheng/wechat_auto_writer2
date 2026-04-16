# 📝 WeChat Auto Writer - 公众号文章智能写作助手

> AI自动生成公众号文章，一键上传到草稿箱

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)

---

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 🤖 **多模型支持** | OpenAI GPT / Claude / SiliconFlow / Ollama 本地模型，可切换 |
| 📝 **文章生成** | 输入主题，一键生成完整公众号文章 |
| 📋 **模板管理** | 保存常用写作模板，提高效率 |
| 📤 **草稿上传** | 自动上传到微信公众号草稿箱 |
| 📚 **历史记录** | 管理已生成文章，支持重新编辑上传 |
| 🎨 **多种风格** | 科普、故事、干货、互动等风格可选 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp config/.env.example .env

# 编辑 .env 文件，配置你的 API Keys
```

**必需配置**：

```env
# 至少配置一种AI模型
OPENAI_API_KEY=sk-xxx              # OpenAI API Key
# 或
CLAUDE_API_KEY=xxx                 # Claude API Key
# 或（推荐国内用户）
SILICONFLOW_API_KEY=xxx            # SiliconFlow API Key
SILICONFLOW_MODEL=Qwen/Qwen2.5-7B-Instruct

# 微信公众号配置（可选，用于上传草稿）
WECHAT_APP_ID=你的AppID
WECHAT_APP_SECRET=你的AppSecret
```

### 3. 启动应用

```bash
streamlit run app.py
```

访问 `http://localhost:8501` 即可使用！

---

## 📖 使用指南

### 生成文章

1. 在侧边栏选择 **AI模型**（OpenAI/Claude/Ollama）
2. 选择 **文章风格**（科普/故事/干货/互动）
3. 可选择 **模板**（可选）
4. 设置 **目标字数**（500-2000）
5. 输入 **文章主题**
6. 点击 **🚀 生成文章**

### 上传到微信

1. 生成文章后，可编辑内容
2. 点击 **📤 上传到微信草稿箱**
3. 在微信公众号后台查看草稿

---

## 🏗️ 项目结构

```
wechat_auto_writer2/
├── app.py                 # 主入口
├── requirements.txt       # 依赖
├── config/
│   ├── settings.py        # 配置管理
│   └── .env.example       # 配置模板
├── core/
│   ├── ai_writer.py       # AI生成引擎
│   ├── wechat_api.py      # 微信API封装
│   └── template_manager.py # 模板管理
├── database/
│   ├── models.py          # 数据模型
│   └── db_manager.py      # 数据库操作
├── ui/pages/
│   ├── article_gen.py     # 文章生成页面
│   ├── templates.py       # 模板管理页面
│   ├── history.py         # 历史记录页面
│   └── settings.py        # 设置页面
└── data/
    └── wechat_writer.db   # 数据库文件
```

---

## 🔧 配置说明

### AI模型配置

| 模型 | 配置项 | 说明 |
|------|--------|------|
| **OpenAI** | `OPENAI_API_KEY`, `OPENAI_MODEL` | 推荐 `gpt-4o-mini`，成本低 |
| **Claude** | `CLAUDE_API_KEY`, `CLAUDE_MODEL` | 写作质量高 |
| **SiliconFlow** | `SILICONFLOW_API_KEY`, `SILICONFLOW_MODEL` | 国内平台，性价比高，推荐 |
| **Ollama** | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | 本地模型，免费 |

**SiliconFlow 推荐模型**：
- `Qwen/Qwen2.5-7B-Instruct`（免费额度）
- `deepseek-ai/DeepSeek-V2.5`（性价比高）
- `Qwen/Qwen2.5-72B-Instruct`（更强大）

### 微信公众号配置

1. 登录 [微信公众平台](https://mp.weixin.qq.com)
2. 进入「设置与开发」→「基本配置」
3. 获取 **AppID** 和 **AppSecret**
4. 配置服务器IP白名单（可选）

---

## 📦 部署

### Streamlit Cloud（推荐）

1. Fork 或 Clone 本仓库到 GitHub
2. 登录 [Streamlit Cloud](https://streamlit.io/cloud)
3. 点击「New app」→ 选择 GitHub 仓库
4. 配置 Secrets（在 Settings → Secrets 中粘贴）：

```toml
# 必需：至少配置一种AI模型
OPENAI_API_KEY = "sk-xxx"
# 或使用 SiliconFlow（推荐国内用户）
SILICONFLOW_API_KEY = "xxx"
SILICONFLOW_MODEL = "Qwen/Qwen2.5-7B-Instruct"

# 微信公众号配置
WECHAT_APP_ID = "wxxxx"
WECHAT_APP_SECRET = "xxx"

# 默认模型
DEFAULT_AI_MODEL = "siliconflow"

# 可选：钉钉通知
# DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
```

5. 点击「Deploy」

**配置说明**：
- Secrets 优先级高于 `.env` 文件
- 参考 `.streamlit/secrets.toml.example` 查看完整配置项
- 不要在 Secrets 中提交 `.env` 文件内容，只配置需要的项

### 本地运行

```bash
streamlit run app.py
```

---

## 🧪 测试

```bash
# 验证配置
python tests/verify_config.py

# 测试AI生成
python tests/demo_ai_writer.py

# 运行所有测试
pytest tests/
```

---

## ⚠️ 注意事项

- 微信API每天获取Token次数有限（约200次），已实现缓存避免频繁请求
- 文章内容必须是HTML格式，否则微信API会报错
- Ollama本地模型需先安装并启动服务：`ollama serve`
- `.env` 文件不要提交到Git，包含敏感信息

---

## 📄 License

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**Made with ❤️ by AI Agents Orchestra**