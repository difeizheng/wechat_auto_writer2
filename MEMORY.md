# 项目记忆文档 (MEMORY.md)

> 本文档记录 WeChat Auto Writer 项目的重要技术决策、问题修复和功能实现。

---

## 1. 微信API 45003/45004 错误修复

### 问题描述
调用微信草稿上传API时，频繁收到错误码：
- **45003**: 标题字段超过限制（最多64字符）
- **45004**: 描述字段超过限制（最多120字符）

### 根本原因
1. JSON编码时使用默认的 `ensure_ascii=True`，导致中文字符被转义成 `\uXXXX` 格式
2. 转义后的字符串长度是原始长度约5倍（每个中文变成6个字符）
3. 摘要字段超过120字符时未做截断处理

### 解决方案

**文件**: `core/wechat_api.py`

1. **JSON编码修改** (行1226-1234):
```python
# 关键修复：使用 ensure_ascii=False 保持中文字符原样
json_str = json.dumps(json_data, ensure_ascii=False)
response = requests.post(
    url,
    params=params,
    data=json_str.encode('utf-8'),
    timeout=timeout,
    headers={"Content-Type": "application/json; charset=utf-8"}
)
```

2. **摘要字段处理** (行590-595):
```python
# digest 超过120字符时不传，让微信自动从正文截取
if raw_digest and len(raw_digest) <= 120:
    formatted_article["digest"] = raw_digest
elif raw_digest and len(raw_digest) > 120:
    # 不传digest字段，微信自动截取正文前54字
```

3. **标题自动截断** (行567-572):
```python
title = raw_title[:64] if len(raw_title) > 64 else raw_title
if len(title) < 5:
    title = f"文章{i+1}"  # 微信要求标题最少5字符
```

---

## 2. 历史记录编辑功能

### 新增功能
在历史记录页面添加完整的文章编辑界面，支持：
- 标题编辑
- 摘要编辑
- 内容编辑（HTML格式）
- 风格切换

### 实现位置
**文件**: `ui/pages/history.py`

新增函数：
- `show_edit_interface(article)` - 显示编辑界面
- `save_edited_article()` - 保存编辑后的文章

### 代码结构
```python
def show_edit_interface(article):
    # 编辑表单
    edited_title = st.text_input("标题", article.title, max_chars=64)
    edited_digest = st.text_area("摘要", article.digest, max_chars=120)
    edited_content = st.text_area("正文内容（HTML）", article.content, height=400)
    edited_style = st.selectbox("风格", ["科普", "故事", "干货", "互动"])
    
    # 保存按钮
    if st.button("保存修改"):
        db_manager.update_article(article.id, {...})
```

---

## 3. 封面图管理功能

### 数据库变更
**文件**: `database/models.py`

Article模型新增字段：
```python
@dataclass
class Article:
    cover_image_path: str = ""  # 封面图路径（本地保存）
```

### 数据库迁移
**文件**: `database/db_manager.py`

新增迁移逻辑：
```sql
ALTER TABLE articles ADD COLUMN cover_image_path TEXT DEFAULT '';
```

### 功能实现
1. **生成文章时保存封面图**
   - 封面图保存路径：`data/covers/{article_id}_{timestamp}.jpg`
   - 自动从生成结果中提取封面图URL并下载

2. **历史记录页面快速上传**
   - 支持上传新封面图
   - 支持替换现有封面图
   - 上传后可直接同步到微信草稿

### 目录结构
```
data/
├── covers/           # 封面图存储目录
│   ├── 1_20260416_abc123.jpg
│   └── 2_20260416_def456.jpg
├── wechat_writer.db  # SQLite数据库
└── token_cache.json  # Token缓存
```

---

## 4. 定时任务系统

### 系统架构

```
┌─────────────────────────────────────────────────────┐
│                 定时任务系统架构                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  config/settings.py                                 │
│  ├── DINGTALK_WEBHOOK                               │
│  └── DINGTALK_SECRET                                │
│                                                     │
│  core/scheduler.py                                  │
│  ├── DingTalkNotifier (钉钉通知)                     │
│  ├── TaskExecutor (任务执行器)                       │
│  └── Scheduler (调度器)                              │
│                                                     │
│  database/db_manager.py                             │
│  ├── scheduled_tasks 表                             │
│                                                     │
│  ui/pages/scheduler.py                              │
│  ├── 任务创建界面                                    │
│  ├── 任务列表界面                                    │
│  └── 立即执行按钮                                    │
│                                                     │
│  scripts/run_scheduler.py                           │
│  ├── 独立运行脚本                                    │
│  └── 后台服务启动                                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 核心模块

**文件**: `core/scheduler.py`

#### 任务类型
```python
class TaskType(str, Enum):
    GENERATE_ARTICLE = "generate_article"   # 生成文章
    UPLOAD_WECHAT = "upload_wechat"         # 上传微信
    FULL_WORKFLOW = "full_workflow"         # 完整流程
```

#### 任务状态
```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"
```

#### 任务数据模型
```python
@dataclass
class ScheduledTask:
    id: Optional[int]
    name: str
    task_type: str
    schedule_time: str         # cron或简单时间格式
    config: Dict               # 任务配置JSON
    status: str
    last_run_time: datetime
    last_run_result: str
    next_run_time: datetime
    is_active: bool
```

### 任务执行器

```python
class TaskExecutor:
    def __init__(self, settings, db_manager):
        self.settings = settings
        self.db_manager = db_manager
        self.dingtalk = DingTalkNotifier(...)
    
    def execute_task(self, task) -> Dict:
        # 根据task_type执行不同逻辑
        if task.task_type == "generate_article":
            return self._execute_generate_article(task)
        elif task.task_type == "upload_wechat":
            return self._execute_upload_wechat(task)
        elif task.task_type == "full_workflow":
            return self._execute_full_workflow(task)
```

### UI页面

**文件**: `ui/pages/scheduler.py`

功能：
- 创建新任务（选择类型、配置时间、设置参数）
- 查看任务列表
- 立即执行任务
- 查看执行历史
- 启用/禁用任务

---

## 5. 钉钉通知签名验证

### 背景
钉钉机器人支持三种安全设置：
1. 自定义关键词
2. IP地址白名单
3. **加签验证**（本项目使用）

### 加签算法

```python
def _generate_sign(self) -> tuple:
    """生成签名
    
    算法：
    1. timestamp = 当前时间戳（毫秒）
    2. stringToSign = timestamp + "\\n" + secret
    3. sign = HMAC-SHA256(secret, stringToSign) -> base64 -> URL编码
    """
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{self.secret}"
    
    # HMAC-SHA256
    hmac_code = hmac.new(
        self.secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    
    # Base64 + URL编码
    sign = base64.b64encode(hmac_code).decode('utf-8')
    sign = urllib.parse.quote_plus(sign)
    
    return timestamp, sign
```

### 配置示例

**文件**: `config/.env.example`

```env
# 钉钉机器人配置（可选）
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=SECxxx...
```

### 配置帮助
1. 创建钉钉群机器人
2. 安全设置选择"加签"
3. 复制Webhook URL和Secret到`.env`

---

## 6. AIWriter初始化修复

### 问题
scheduler.py 中创建AIWriter实例时未传入settings参数，导致：
- 无法获取API配置
- 无法切换模型
- 配置读取失败

### 修复位置
**文件**: `core/scheduler.py` 行395

```python
# 修复：传入settings参数
writer = AIWriter(model=model, settings=self.settings)
```

### AIWriter构造函数
```python
class AIWriter:
    def __init__(self, model: str = None, settings: any = None):
        self.settings = settings or get_settings()
        self.model = model or self.settings.DEFAULT_AI_MODEL
        # ...
```

---

## 7. 定时任务封面图路径缺失修复

### 问题
`full_workflow` 任务执行时报错："生成成功但上传失败: 全部失败: 1 个错误"
- 任务配置中只有 `cover_image_uploaded: True`
- 缺少 `cover_image_path` 字段
- 生成的文章没有封面图，上传失败

### 根因
`ui/pages/scheduler.py` 第323-324行：
- 上传封面图后只设置了标志位
- 未保存封面图文件到本地
- 未记录文件路径到任务配置

### 修复
**文件**: `ui/pages/scheduler.py` 第323-332行

```python
if cover_image:
    import os
    import uuid
    covers_dir = os.path.join("data", "covers")
    os.makedirs(covers_dir, exist_ok=True)
    cover_ext = os.path.splitext(cover_image.name)[1] or ".jpg"
    cover_filename = f"task_cover_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d')}{cover_ext}"
    cover_path = os.path.join(covers_dir, cover_filename)
    with open(cover_path, "wb") as f:
        f.write(cover_image.getbuffer())
    task_config["cover_image_uploaded"] = True
    task_config["cover_image_path"] = cover_path
    st.success(f"封面图已保存: {cover_filename}")
```

### 验证
- 封面图保存到 `data/covers/task_cover_xxx.jpg`
- 任务配置包含 `cover_image_path` 字段
- scheduler.py:608 能正确获取封面图路径

---

## 7. 重要技术决策总结

### JSON编码策略
- 所有微信API请求使用 `ensure_ascii=False`
- 请求头设置 `charset=utf-8`
- 避免中文转义导致长度膨胀

### 字段长度处理
- 标题：自动截断至64字符，少于5字符自动补充
- 摘要：超过120字符不传，让微信自动处理
- 作者：最多8字符（微信限制）

### Token缓存策略
- 文件缓存：`data/token_cache.json`
- 有效期：7000秒（官方7200秒，提前200秒刷新）
- 提前5分钟检查过期

### 钉钉通知策略
- 任务成功/失败都发送通知
- 支持加签验证（推荐）
- 发送失败不阻塞任务执行

### 定时任务调度
- 后台线程运行，每60秒检查一次
- 支持立即执行模式
- 任务执行后自动更新状态

---

## 8. 待完善功能

### 优先级高
1. [ ] scheduled_tasks表完整CRUD操作
2. [ ] 定时任务cron表达式完整解析
3. [ ] 任务执行日志详细记录

### 优先级中
1. [ ] 封面图自动生成（AI生成）
2. [ ] 批量文章生成优化
3. [ ] 任务执行失败重试机制

### 优先级低
1. [ ] 多公众号支持
2. [ ] 文章排版模板
3. [ ] 数据导出功能

---

## 9. 文件清单

### 新增文件
```
core/scheduler.py           # 定时任务核心模块
ui/pages/scheduler.py       # 定时任务UI页面
scripts/run_scheduler.py    # 调度器运行脚本
MEMORY.md                   # 本记忆文档
```

### 修改文件
```
core/wechat_api.py          # JSON编码修复、字段长度处理
database/models.py          # 新增cover_image_path字段
database/db_manager.py      # 数据库迁移、封面图字段
ui/pages/history.py         # 编辑界面、封面图管理
config/settings.py          # 钉钉配置项
```

---

## 10. 环境配置清单

### 本地开发 (.env)
```env
# 必需配置
OPENAI_API_KEY=sk-xxx
WECHAT_APP_ID=wxxxx
WECHAT_APP_SECRET=xxx

# 可选配置
DEFAULT_AI_MODEL=gpt-4o-mini
SILICONFLOW_API_KEY=xxx
CLAUDE_API_KEY=xxx
OLLAMA_BASE_URL=http://localhost:11434

# 钉钉通知（可选）
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=SECxxx
```

### Streamlit Cloud (secrets.toml)
在 Dashboard → Settings → Secrets 中配置：

```toml
OPENAI_API_KEY = "sk-xxx"
SILICONFLOW_API_KEY = "xxx"
WECHAT_APP_ID = "wxxxx"
WECHAT_APP_SECRET = "xxx"
DEFAULT_AI_MODEL = "siliconflow"
```

### 配置优先级
1. Streamlit secrets (st.secrets) - 最高优先级
2. 环境变量 (.env)
3. 默认值

---

## 11. Streamlit Secrets 支持

### 功能实现
`config/settings.py` 新增 `_get_streamlit_secret()` 函数，支持从 Streamlit Cloud secrets 读取配置。

### 配置文件
- `.streamlit/secrets.toml.example` - 配置模板
- `.streamlit/config.toml` - Streamlit 主题配置
- `.streamlit/secrets.toml` - 本地 secrets（不提交 Git）

### 部署方法
1. Fork 仓库到 GitHub
2. Streamlit Cloud 创建新应用
3. Settings → Secrets 粘贴配置
4. Deploy

---

*文档生成时间: 2026-04-16*
*项目版本: v1.0*