# Project: WeChat Auto Writer

公众号文章智能写作助手 - Python + Streamlit + 微信API

## Setup

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp config/.env.example .env
# 编辑 .env 文件，配置 API Keys

# 3. 启动应用
streamlit run app.py
```

## Commands

| 命令 | 说明 |
|------|------|
| `streamlit run app.py` | 启动Web应用 |
| `python tests/verify_config.py` | 验证配置是否正确 |
| `python tests/demo_ai_writer.py` | 测试AI生成功能 |
| `pytest tests/` | 运行所有测试 |

## Architecture

```
app.py               # Streamlit主入口
config/
  settings.py        # 配置管理（.env加载）
core/
  ai_writer.py       # AI生成引擎（OpenAI/Claude/Ollama）
  wechat_api.py      # 微信API封装（草稿上传）
  template_manager.py # 模板管理
database/
  models.py          # 数据模型（Article/Template）
  db_manager.py      # SQLite CRUD操作
ui/pages/
  article_gen.py     # 文章生成页面（核心）
  templates.py       # 模板管理页面
  history.py         # 历史记录页面
  settings.py        # 设置页面
```

## Key Modules

### AI Writer (`core/ai_writer.py`)
- 多模型支持：OpenAI GPT / Claude / SiliconFlow / Ollama
- 运行时切换：`writer.switch_model("siliconflow")`
- 统一接口：`generate_article(topic, style, word_count)`
- 返回格式：`{title, content, digest, keywords}`
- 模型名称配置：可在 `.env` 中自定义每个模型的名称

### WeChat API (`core/wechat_api.py`)
- Token缓存：文件缓存，2小时有效期
- 草稿上传：`add_draft(articles)` → 返回 `media_id`
- 图片上传：`upload_image(path)` → 返回 `{media_id, url}`
- 自动重试：Token失效时自动刷新

### Database (`database/`)
- SQLite单文件：`data/wechat_writer.db`
- 文章表：`articles`（标题、内容、状态、草稿ID）
- 模板表：`templates`（4个默认模板）
- 软删除：模板删除为 `is_active=0`

## Conventions

1. **配置优先级**：`.env` 文件 > 环境变量 > 默认值
2. **敏感信息**：不写入代码，`.env` 不提交Git
3. **HTML内容**：文章正文必须是HTML格式（微信API要求）
4. **中文界面**：所有UI和错误信息使用中文
5. **模型选择**：默认使用 `gpt-4o-mini`（成本低），可在设置中切换
6. **SiliconFlow**：国内用户推荐使用，性价比高，新用户有免费额度

## Error Handling

- AI调用失败：重试3次，显示友好中文错误
- Token过期：自动刷新，错误码40014/42001
- 配置缺失：启动时验证，提示用户配置

## Deployment

### 本地运行
```bash
streamlit run app.py
```

### Streamlit Cloud
1. 上传到GitHub
2. 连接Streamlit Cloud
3. 配置 `secrets.toml`（替代.env）
4. 自动部署

## Important Notes

- 微信API每天获取Token次数有限（约200次），已实现缓存避免频繁请求
- 文章内容必须HTML格式，否则微信API会报错
- Ollama本地模型需先安装并启动服务：`ollama serve`