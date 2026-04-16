"""
微信公众号API封装
实现草稿上传、素材管理等功能

功能特性：
- access_token 自动缓存与刷新
- 草稿箱管理（新增、列表、删除）
- 素材上传（图片）
- 完善的错误处理与重试机制
- 调用频率限制考虑
"""
import requests
import json
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Union, Any

# 配置日志
logger = logging.getLogger(__name__)


# ==================== 异常类 ====================

class WeChatAPIError(Exception):
    """微信API错误
    
    封装微信API返回的错误信息，提供友好的中文错误提示。
    
    Attributes:
        code: 错误码
        message: 错误信息（中文）
        original_msg: 微信原始错误信息
    """
    
    # 微信API常见错误码映射（中文友好提示）
    ERROR_MESSAGES = {
        -1: "系统繁忙，请稍后重试",
        0: "请求成功",
        40001: "AppSecret 错误或不属于该公众号",
        40002: "请确保grant_type字段值为client_credential",
        40003: "不合法的OpenID",
        40004: "不合法的媒体文件类型",
        40007: "不合法的media_id",
        40008: "不合法的消息类型",
        40009: "不合法的图片文件大小",
        40013: "不合法的AppID",
        40014: "不合法的access_token",
        40015: "不合法的菜单类型",
        40016: "不合法的按钮个数",
        40017: "不合法的按钮类型",
        40018: "不合法的按钮名字长度",
        40019: "不合法的按钮KEY长度",
        40020: "不合法的按钮URL长度",
        40021: "不合法的菜单版本号",
        40022: "不合法的子菜单级数",
        40023: "不合法的子菜单按钮个数",
        40024: "不合法的子菜单按钮类型",
        40025: "不合法的子菜单按钮名字长度",
        40026: "不合法的子菜单按钮KEY长度",
        40027: "不合法的子菜单按钮URL长度",
        40028: "不合法的自定义菜单使用用户",
        40029: "不合法的oauth_code",
        40030: "不合法的refresh_token",
        40031: "不合法的openid列表",
        40032: "不合法的openid列表长度",
        40033: "不合法的请求字符",
        40035: "不合法的参数",
        40036: "不合法的模板id长度",
        40037: "不合法的模板id",
        40038: "不合法的模板消息内容",
        40039: "不合法的url",
        40050: "不合法的分组id",
        40051: "分组名字不合法",
        40117: "分组名字不合法",
        41001: "缺少access_token参数",
        41002: "缺少appid参数",
        41003: "缺少refresh_token参数",
        41004: "缺少secret参数",
        41005: "缺少多媒体文件数据",
        41006: "缺少media_id参数",
        41007: "缺少子菜单数据",
        41008: "缺少oauth code",
        41009: "缺少openid",
        42001: "access_token 获取次数已达到上限，请检查缓存策略",
        42002: "refresh_token 已过期",
        42003: "oauth_code 已过期",
        42007: "测试用户无体验接口权限",
        43001: "需要GET请求",
        43002: "需要POST请求",
        43003: "需要HTTPS请求",
        43004: "需要接收者关注",
        43005: "需要好友关系",
        44001: "多媒体文件为空",
        44002: "POST的数据包为空",
        44003: "图文消息内容为空",
        44004: "文本消息内容为空",
        45001: "多媒体文件大小超过限制",
        45002: "消息内容超过限制",
        45003: "标题字段超过限制",
        45004: "描述字段超过限制",
        45005: "链接字段超过限制",
        45006: "图片链接字段超过限制",
        45007: "语音播放时间超过限制",
        45008: "图文消息超过限制",
        45009: "接口调用超过限制",
        45010: "创建菜单个数超过限制",
        45011: "API调用太频繁，请稍候再试",
        45015: "回复时间超过限制",
        45016: "系统分组，不允许修改",
        45017: "分组名字过长",
        45018: "分组数量超过上限",
        45056: "创建的标签数量过多",
        45057: "该标签下粉丝数量超过上限",
        45058: "不能修改0号标签",
        45059: "标签名已经存在",
        46001: "不存在媒体数据",
        46002: "不存在的菜单版本",
        46003: "不存在的菜单数据",
        46004: "不存在的用户",
        47001: "解析JSON/XML内容错误",
        48001: "api功能未授权",
        48002: "粉丝拒绝接收消息",
        48003: "该公众号已封禁",
        48004: "api接口被封禁",
        48005: "api禁止调用被封禁的api功能",
        48006: "api禁止调用低版本的api功能",
        50001: "用户未授权该api",
        50002: "用户授权该api次数用完",
        50003: "用户无该api的调用权限",
        50004: "该api权限被限制调用",
        50005: "用户未绑定微信号",
        60001: "公众号未绑定开放平台帐号",
        60002: "公众号已绑定开放平台帐号",
        60003: "该开放平台帐号已绑定公众号",
        60004: "开放平台帐号绑定公众号超过上限",
        60005: "该公众号未绑定开放平台帐号，无法获取unionid",
        60007: "该帐号已在其他开放平台帐号绑定",
        87009: "图文消息内容涉嫌违反相关规定",
        87010: "图文消息标题涉嫌违反相关规定",
        87011: "图文消息封面涉嫌违反相关规定",
        87012: "图文消息正文涉嫌违反相关规定",
        87013: "图文消息留言涉嫌违反相关规定",
        45065: "相同的多图文消息已存在，请勿重复添加",
        45066: "草稿箱功能未开启",
        45067: "文章封面不能为空",
        45068: "文章标题不能为空",
        45069: "文章内容不能为空",
        45070: "文章作者不能为空",
        45071: "草稿不存在",
        45072: "草稿修改失败",
        45073: "草稿删除失败",
    }
    
    def __init__(self, code: int, message: str = None, original_msg: str = None):
        """初始化异常
        
        Args:
            code: 微信API错误码
            message: 自定义错误信息（可选）
            original_msg: 微信原始错误信息（可选）
        """
        self.code = code
        self.original_msg = original_msg or message or ""
        
        # 获取中文友好提示
        if message:
            self.message = message
        elif code in self.ERROR_MESSAGES:
            self.message = self.ERROR_MESSAGES[code]
        else:
            self.message = f"未知错误（错误码：{code})"
        
        super().__init__(f"[错误码 {code}] {self.message}")
    
    def __str__(self) -> str:
        return f"微信API错误 [{self.code}]: {self.message}"
    
    def __repr__(self) -> str:
        return f"WeChatAPIError(code={self.code}, message='{self.message}')"


class WeChatNetworkError(WeChatAPIError):
    """网络请求错误"""
    
    def __init__(self, message: str):
        super().__init__(-1, f"网络请求失败: {message}", message)


class WeChatTokenExpiredError(WeChatAPIError):
    """Token过期错误"""
    
    def __init__(self):
        super().__init__(42001, "access_token已过期，正在自动刷新...", "access_token expired")


# ==================== Token缓存 ====================

class TokenCache:
    """access_token缓存器
    
    使用本地文件缓存access_token，避免频繁调用微信API。
    
    缓存策略：
    - 本地文件缓存，路径：data/token_cache.json
    - 有效期：7000秒（官方为7200秒，提前200秒刷新）
    - 提前5分钟（300秒）检查过期，确保有足够时间刷新
    
    文件格式：
    {
        "token": "ACCESS_TOKEN",
        "expires_at": "2026-04-16T10:00:00",
        "app_id": "wx1234567890",
        "created_at": "2026-04-16T08:00:00"
    }
    """
    
    # 缓存文件路径（相对于项目根目录）
    CACHE_FILE = "data/token_cache.json"
    
    # 过期边际时间（秒）- 提前刷新
    EXPIRE_MARGIN = 300  # 5分钟
    
    # 默认有效期（秒）
    DEFAULT_EXPIRES_IN = 7200
    
    def __init__(self, app_id: str = None):
        """初始化缓存器
        
        Args:
            app_id: 微信公众号AppID（用于区分不同公众号）
        """
        self.app_id = app_id
        self._cache_dir = Path(self.CACHE_FILE).parent
    
    def get(self) -> Optional[str]:
        """获取缓存的token
        
        Returns:
            str: 缓存的token，如果不存在或已过期则返回None
        """
        cache_path = Path(self.CACHE_FILE)
        
        if not cache_path.exists():
            logger.debug("Token缓存文件不存在")
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 检查app_id是否匹配（避免多公众号混淆）
            if self.app_id and data.get("app_id") != self.app_id:
                logger.debug(f"Token缓存的app_id不匹配: {data.get('app_id')} != {self.app_id}")
                return None
            
            # 检查是否过期
            expires_at_str = data.get("expires_at")
            if not expires_at_str:
                logger.warning("Token缓存缺少expires_at字段")
                return None
            
            expires_at = datetime.fromisoformat(expires_at_str)
            now = datetime.now()
            
            # 提前EXPIRE_MARGIN秒刷新，避免边界情况
            if now < expires_at - timedelta(seconds=self.EXPIRE_MARGIN):
                remaining = (expires_at - now).total_seconds()
                logger.debug(f"使用缓存的token，剩余有效期：{remaining:.0f}秒")
                return data.get("token")
            
            # 已过期
            logger.info(f"Token缓存已过期，过期时间：{expires_at}")
            return None
            
        except json.JSONDecodeError as e:
            logger.warning(f"Token缓存文件格式错误: {e}")
            return None
        except ValueError as e:
            logger.warning(f"Token缓存时间格式错误: {e}")
            return None
        except Exception as e:
            logger.warning(f"读取Token缓存失败: {e}")
            return None
    
    def set(self, token: str, expires_in: int = None, app_id: str = None) -> None:
        """保存token到缓存
        
        Args:
            token: access_token值
            expires_in: 有效期（秒），默认7200秒
            app_id: 微信公众号AppID
        """
        if expires_in is None:
            expires_in = self.DEFAULT_EXPIRES_IN
        
        # 使用传入的app_id或实例的app_id
        actual_app_id = app_id or self.app_id
        
        # 计算过期时间
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # 构造缓存数据
        data = {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "app_id": actual_app_id or "",
            "created_at": datetime.now().isoformat(),
            "expires_in": expires_in
        }
        
        # 确保目录存在
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入缓存文件
        try:
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Token缓存保存成功，有效期：{expires_in}秒，过期时间：{expires_at}")
            
        except Exception as e:
            logger.error(f"保存Token缓存失败: {e}")
            # 不抛出异常，缓存失败不影响正常使用
    
    def clear(self) -> bool:
        """清除缓存
        
        Returns:
            bool: 是否成功清除
        """
        cache_path = Path(self.CACHE_FILE)
        
        if not cache_path.exists():
            return True
        
        try:
            os.remove(cache_path)
            logger.info("Token缓存已清除")
            return True
        except Exception as e:
            logger.warning(f"清除Token缓存失败: {e}")
            return False
    
    def get_info(self) -> Optional[Dict]:
        """获取缓存信息（不验证过期）
        
        Returns:
            dict: 缓存信息，包含token、expires_at、app_id等
        """
        cache_path = Path(self.CACHE_FILE)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取缓存信息失败: {e}")
            return None


# ==================== 微信API封装 ====================

class WeChatAPI:
    """微信公众号API封装
    
    实现微信公众号的核心API功能：
    - access_token 管理（自动缓存、刷新）
    - 草稿箱管理（新增、列表、删除）
    - 素材上传（图片）
    - 完善的错误处理和重试机制
    
    API基础地址：https://api.weixin.qq.com/cgi-bin
    
    使用示例：
    ```python
    from core.wechat_api import WeChatAPI
    
    # 初始化
    api = WeChatAPI(app_id="wx123456", app_secret="secret123")
    
    # 测试连接
    result = api.test_connection()
    print(result)
    
    # 新增草稿
    media_id = api.add_draft([{
        "title": "文章标题",
        "author": "作者",
        "content": "<p>文章内容</p>",
        "digest": "摘要"
    }])
    
    # 上传图片
    image_result = api.upload_image("path/to/image.jpg")
    ```
    """
    
    # 微信API基础地址
    BASE_URL = "https://api.weixin.qq.com/cgi-bin"
    
    # API调用超时设置（秒）
    DEFAULT_TIMEOUT = 30
    TOKEN_TIMEOUT = 10
    UPLOAD_TIMEOUT = 60
    
    # 重试配置
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 1  # 重试延迟（秒）
    
    # Token刷新相关错误码
    TOKEN_ERROR_CODES = [40014, 42001, 40001]  # token无效/过期/secret错误
    
    def __init__(self, app_id: str, app_secret: str):
        """初始化微信API
        
        Args:
            app_id: 微信公众号AppID
            app_secret: 微信公众号AppSecret
            
        Raises:
            ValueError: 参数无效时抛出
        """
        if not app_id or not app_secret:
            raise ValueError("app_id 和 app_secret 不能为空")
        
        self.app_id = app_id.strip()
        self.app_secret = app_secret.strip()
        self._token_cache = TokenCache(app_id=self.app_id)
        
        # 记录最近的API调用时间（用于频率限制检查）
        self._last_call_time = 0
        self._call_count = 0
        
        logger.info(f"WeChatAPI 初始化成功，app_id: {app_id[:8]}...")
    
    # ==================== Token管理 ====================
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """获取access_token（自动缓存）
        
        缓存策略：
        - 本地文件缓存，有效期7000秒（提前5分钟刷新）
        - 过期前自动刷新
        - 支持强制刷新
        
        Args:
            force_refresh: 是否强制刷新token
            
        Returns:
            str: access_token
            
        Raises:
            WeChatAPIError: 获取token失败时抛出
        """
        # 尝试从缓存获取
        if not force_refresh:
            cached_token = self._token_cache.get()
            if cached_token:
                logger.debug("使用缓存的access_token")
                return cached_token
        
        # 调用微信API获取新token
        logger.info("正在获取新的access_token...")
        
        url = f"{self.BASE_URL}/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret
        }
        
        try:
            response = self._request_with_retry(
                "GET",
                url,
                params=params,
                timeout=self.TOKEN_TIMEOUT,
                retry_on_token_error=False  # 获取token时不重试token错误
            )
            
            data = response.json()
            
            if "access_token" in data:
                token = data["access_token"]
                expires_in = data.get("expires_in", 7200)
                
                # 保存到缓存
                self._token_cache.set(token, expires_in, self.app_id)
                
                logger.info(f"获取新access_token成功，有效期{expires_in}秒")
                return token
            
            # 错误处理
            errcode = data.get("errcode", -1)
            errmsg = data.get("errmsg", "未知错误")
            raise WeChatAPIError(errcode, errmsg)
            
        except requests.RequestException as e:
            logger.error(f"请求微信API失败: {e}")
            raise WeChatNetworkError(str(e))
    
    def refresh_token(self) -> str:
        """强制刷新access_token
        
        Returns:
            str: 新的access_token
        """
        logger.info("强制刷新access_token")
        self._token_cache.clear()
        return self.get_access_token(force_refresh=True)
    
    # ==================== 草稿箱管理 ====================
    
    def add_draft(self, articles: List[Dict], auto_retry: bool = True) -> Dict:
        """新增草稿
        
        Args:
            articles: 文章列表，每篇文章包含：
                - title: 标题（必填，最少5字符，最多64字符，超出会自动截断）
                - author: 作者（可选，最多8字符）
                - digest: 摘要（可选，最多120字符，超出会自动截取内容前120字符）
                - content: 正文内容（必填，HTML格式，最多20000字符）
                - content_source_url: 原文链接（可选）
                - thumb_media_id: 封面图素材ID（可选，使用upload_image获取）
                - need_open_comment: 是否打开评论（0否/1是，默认0）
                - only_fans_can_comment: 是否粉丝可评论（0否/1是，默认0）
            auto_retry: token失效时是否自动重试
                
        Returns:
            dict: {"media_id": "xxx"}  草稿ID
            
        Raises:
            WeChatAPIError: 上传失败时抛出
            ValueError: 参数验证失败时抛出
        
        Note:
            微信公众号API对字段长度有严格限制：
            - 标题：5-64字符（少于5字符会自动补充，多于64字符会截断）
            - 摘要：最多120字符（超出会截断）
            - 作者：最多8字符
        """
        # 参数验证
        if not articles or len(articles) == 0:
            raise ValueError("文章列表不能为空")
        
        if len(articles) > 8:
            raise ValueError("单次最多上传8篇文章")
        
        # 验证每篇文章的字段
        for i, article in enumerate(articles):
            if not article.get("title"):
                raise ValueError(f"第{i+1}篇文章缺少标题")
            if not article.get("content"):
                raise ValueError(f"第{i+1}篇文章缺少内容")
        
        # 构造请求数据
        # 微信API要求articles中的每个article需要包含特定字段
        # 并进行长度限制处理
        formatted_articles = []
        for i, article in enumerate(articles):
            # 标题处理：微信要求5-64字符
            raw_title = article.get("title", "")
            title = raw_title[:64] if len(raw_title) > 64 else raw_title
            if len(title) < 5:
                # 标题少于5字符时，补充默认标题
                title = f"文章{i+1}"
                logger.warning(f"第{i+1}篇文章标题少于5字符，已自动补充为: {title}")
            
            # 摘要处理：微信官方文档限制120字符，但实际可能更短
            # 参考：如果digest不传，微信会自动抓取正文前54字
            # 策略：digest超过120字符或为空时不传，让微信自动处理
            raw_digest = article.get("digest", "")
            
            # 构造文章数据 - 核心字段
            formatted_article = {
                "title": title,
                "author": article.get("author", ""),
                "content": article.get("content", ""),
                "content_source_url": article.get("content_source_url", ""),
                "thumb_media_id": article.get("thumb_media_id", ""),
                "need_open_comment": article.get("need_open_comment", 0),
                "only_fans_can_comment": article.get("only_fans_can_comment", 0),
            }
            
            # digest 字段处理：只有长度合适时才传，否则让微信自动截取
            if raw_digest and len(raw_digest) <= 120:
                formatted_article["digest"] = raw_digest
            elif raw_digest and len(raw_digest) > 120:
                # 超过120字符，不传digest，让微信自动从正文截取
                logger.warning(f"第{i+1}篇文章摘要超过120字符，不传digest字段，微信将自动截取正文前54字")
            
            # 记录截断警告
            if len(raw_title) > 64:
                logger.warning(f"第{i+1}篇文章标题超过64字符，已截断: {raw_title[:30]}...")
            
            formatted_articles.append(formatted_article)
        
        data = {"articles": formatted_articles}
        
        # 获取token并发送请求
        token = self.get_access_token()
        url = f"{self.BASE_URL}/draft/add"
        
        try:
            response = self._request_with_retry(
                "POST",
                url,
                params={"access_token": token},
                json_data=data,
                timeout=self.DEFAULT_TIMEOUT,
                retry_on_token_error=auto_retry
            )
            
            result = response.json()
            
            if "media_id" in result:
                media_id = result["media_id"]
                logger.info(f"草稿上传成功，media_id: {media_id}")
                return {"media_id": media_id}
            
            # 错误处理
            errcode = result.get("errcode", -1)
            errmsg = result.get("errmsg", "未知错误")
            raise WeChatAPIError(errcode, errmsg)
            
        except requests.RequestException as e:
            logger.error(f"上传草稿网络错误: {e}")
            raise WeChatNetworkError(str(e))
    
    def get_draft_list(self, offset: int = 0, count: int = 10, no_content: bool = False) -> Dict:
        """获取草稿列表
        
        Args:
            offset: 偏移量（从全部素材的第offset个开始返回）
            count: 返回数量（1-20）
            no_content: 是否不返回content字段（节省流量）
                
        Returns:
            dict: {
                "total_count": 总数量,
                "item_count": 本次返回数量,
                "item": [
                    {
                        "media_id": 草稿ID,
                        "content": {
                            "news_item": [
                                {
                                    "title": 标题,
                                    "author": 作者,
                                    "digest": 摘要,
                                    "content": 内容（如果no_content=False）,
                                    "thumb_media_id": 封面图ID
                                }
                            ]
                        },
                        "update_time": 更新时间戳
                    }
                ]
            }
            
        Raises:
            WeChatAPIError: 获取失败时抛出
        """
        # 参数验证
        if count < 1 or count > 20:
            raise ValueError("count 必须在 1-20 之间")
        
        if offset < 0:
            raise ValueError("offset 不能为负数")
        
        token = self.get_access_token()
        url = f"{self.BASE_URL}/draft/batchget"
        
        data = {
            "offset": offset,
            "count": count,
            "no_content": 1 if no_content else 0
        }
        
        try:
            response = self._request_with_retry(
                "POST",
                url,
                params={"access_token": token},
                json_data=data,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            result = response.json()
            
            if "errcode" in result and result["errcode"] != 0:
                errcode = result.get("errcode", -1)
                errmsg = result.get("errmsg", "未知错误")
                raise WeChatAPIError(errcode, errmsg)
            
            total_count = result.get("total_count", 0)
            item_count = result.get("item_count", 0)
            logger.info(f"获取草稿列表成功，总数：{total_count}，本次返回：{item_count}")
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"获取草稿列表网络错误: {e}")
            raise WeChatNetworkError(str(e))
    
    def get_draft(self, media_id: str) -> Dict:
        """获取单个草稿详情
        
        Args:
            media_id: 草稿ID
                
        Returns:
            dict: 草稿详情
            
        Raises:
            WeChatAPIError: 获取失败时抛出
        """
        if not media_id:
            raise ValueError("media_id 不能为空")
        
        token = self.get_access_token()
        url = f"{self.BASE_URL}/draft/get"
        
        data = {"media_id": media_id}
        
        try:
            response = self._request_with_retry(
                "POST",
                url,
                params={"access_token": token},
                json_data=data,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            result = response.json()
            
            if "errcode" in result and result["errcode"] != 0:
                errcode = result.get("errcode", -1)
                errmsg = result.get("errmsg", "未知错误")
                raise WeChatAPIError(errcode, errmsg)
            
            logger.info(f"获取草稿详情成功，media_id: {media_id}")
            return result
            
        except requests.RequestException as e:
            logger.error(f"获取草稿详情网络错误: {e}")
            raise WeChatNetworkError(str(e))
    
    def delete_draft(self, media_id: str) -> bool:
        """删除草稿
        
        Args:
            media_id: 草稿ID
                
        Returns:
            bool: 是否删除成功
            
        Raises:
            WeChatAPIError: 删除失败时抛出
        """
        if not media_id:
            raise ValueError("media_id 不能为空")
        
        token = self.get_access_token()
        url = f"{self.BASE_URL}/draft/delete"
        
        data = {"media_id": media_id}
        
        try:
            response = self._request_with_retry(
                "POST",
                url,
                params={"access_token": token},
                json_data=data,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            result = response.json()
            
            errcode = result.get("errcode", -1)
            if errcode == 0:
                logger.info(f"草稿删除成功：{media_id}")
                return True
            
            errmsg = result.get("errmsg", "未知错误")
            raise WeChatAPIError(errcode, errmsg)
            
        except requests.RequestException as e:
            logger.error(f"删除草稿网络错误: {e}")
            raise WeChatNetworkError(str(e))
    
    def update_draft(self, media_id: str, articles: List[Dict], index: int = None) -> bool:
        """修改草稿
        
        Args:
            media_id: 草稿ID
            articles: 要更新的文章列表
            index: 要更新的文章索引（可选，不指定则更新全部）
                
        Returns:
            bool: 是否更新成功
            
        Raises:
            WeChatAPIError: 更新失败时抛出
        """
        if not media_id:
            raise ValueError("media_id 不能为空")
        
        token = self.get_access_token()
        url = f"{self.BASE_URL}/draft/update"
        
        # 构造请求数据
        data = {
            "media_id": media_id,
            "articles": articles
        }
        
        if index is not None:
            data["index"] = index
        
        try:
            response = self._request_with_retry(
                "POST",
                url,
                params={"access_token": token},
                json_data=data,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            result = response.json()
            
            errcode = result.get("errcode", -1)
            if errcode == 0:
                logger.info(f"草稿修改成功：{media_id}")
                return True
            
            errmsg = result.get("errmsg", "未知错误")
            raise WeChatAPIError(errcode, errmsg)
            
        except requests.RequestException as e:
            logger.error(f"修改草稿网络错误: {e}")
            raise WeChatNetworkError(str(e))
    
    # ==================== 素材管理 ====================
    
    def upload_image(self, image_path: str, auto_retry: bool = True) -> Dict:
        """上传图片素材
        
        上传图片到微信公众号素材库，获取media_id用于草稿封面等。
        
        Args:
            image_path: 图片文件路径
            auto_retry: token失效时是否自动重试
                
        Returns:
            dict: {
                "media_id": "xxx",  # 素材ID
                "url": "xxx"        # 图片URL（永久素材才有）
            }
            
        Raises:
            WeChatAPIError: 上传失败时抛出
            FileNotFoundError: 图片文件不存在
            ValueError: 图片格式不支持
        """
        # 检查文件是否存在
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"图片文件不存在：{image_path}")
        
        # 检查文件大小（微信限制2MB）
        file_size = image_file.stat().st_size
        if file_size > 2 * 1024 * 1024:
            raise ValueError(f"图片文件过大（{file_size/1024/1024:.2f}MB），微信限制最大2MB")
        
        # 检查文件格式
        valid_formats = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]
        if image_file.suffix.lower() not in valid_formats:
            raise ValueError(f"不支持的图片格式：{image_file.suffix}，支持：{valid_formats}")
        
        token = self.get_access_token()
        url = f"{self.BASE_URL}/material/add_material"
        
        try:
            # 读取图片文件
            with open(image_file, "rb") as f:
                files = {"media": (image_file.name, f, f"image/{image_file.suffix[1:]}")}
                params = {
                    "access_token": token,
                    "type": "image"
                }
                
                response = self._request_with_retry(
                    "POST",
                    url,
                    params=params,
                    files=files,
                    timeout=self.UPLOAD_TIMEOUT,
                    retry_on_token_error=auto_retry
                )
            
            result = response.json()
            
            if "media_id" in result:
                media_id = result["media_id"]
                url_str = result.get("url", "")
                logger.info(f"图片上传成功，media_id: {media_id}")
                return {"media_id": media_id, "url": url_str}
            
            # 错误处理
            errcode = result.get("errcode", -1)
            errmsg = result.get("errmsg", "未知错误")
            raise WeChatAPIError(errcode, errmsg)
            
        except requests.RequestException as e:
            logger.error(f"上传图片网络错误: {e}")
            raise WeChatNetworkError(str(e))
    
    def upload_temp_image(self, image_path: str) -> Dict:
        """上传临时图片素材
        
        临时素材有效期3天，适用于不需要永久保存的场景。
        
        Args:
            image_path: 图片文件路径
                
        Returns:
            dict: {"media_id": "xxx"}
        """
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"图片文件不存在：{image_path}")
        
        token = self.get_access_token()
        url = f"{self.BASE_URL}/media/upload"
        
        try:
            with open(image_file, "rb") as f:
                files = {"media": (image_file.name, f, f"image/{image_file.suffix[1:]}")}
                params = {
                    "access_token": token,
                    "type": "image"
                }
                
                response = self._request_with_retry(
                    "POST",
                    url,
                    params=params,
                    files=files,
                    timeout=self.UPLOAD_TIMEOUT
                )
            
            result = response.json()
            
            if "media_id" in result:
                logger.info(f"临时图片上传成功，media_id: {result['media_id']}")
                return result
            
            errcode = result.get("errcode", -1)
            errmsg = result.get("errmsg", "未知错误")
            raise WeChatAPIError(errcode, errmsg)
            
        except requests.RequestException as e:
            logger.error(f"上传临时图片网络错误: {e}")
            raise WeChatNetworkError(str(e))
    
    def get_material_list(self, type: str = "image", offset: int = 0, count: int = 10) -> Dict:
        """获取素材列表
        
        Args:
            type: 素材类型（image/video/voice/news）
            offset: 偏移量
            count: 返回数量（1-20）
                
        Returns:
            dict: 素材列表
        """
        token = self.get_access_token()
        url = f"{self.BASE_URL}/material/batchget_material"
        
        data = {
            "type": type,
            "offset": offset,
            "count": count
        }
        
        try:
            response = self._request_with_retry(
                "POST",
                url,
                params={"access_token": token},
                json_data=data,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            result = response.json()
            
            if "errcode" in result and result["errcode"] != 0:
                raise WeChatAPIError(result["errcode"], result.get("errmsg", "未知错误"))
            
            logger.info(f"获取素材列表成功，类型：{type}")
            return result
            
        except requests.RequestException as e:
            logger.error(f"获取素材列表网络错误: {e}")
            raise WeChatNetworkError(str(e))
    
    # ==================== 发布管理 ====================
    
    def publish_draft(self, media_id: str) -> Dict:
        """发布草稿
        
        注意：发布后文章不可删除，只能通过发布成功后的publish_id查询发布状态。
        
        Args:
            media_id: 草稿ID
                
        Returns:
            dict: {
                "publish_id": "xxx",  # 发布任务ID
                "msg_data_id": "xxx"  # 消息数据ID（发布成功后有）
            }
        """
        if not media_id:
            raise ValueError("media_id 不能为空")
        
        token = self.get_access_token()
        url = f"{self.BASE_URL}/freepublish/submit"
        
        data = {"media_id": media_id}
        
        try:
            response = self._request_with_retry(
                "POST",
                url,
                params={"access_token": token},
                json_data=data,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            result = response.json()
            
            if "publish_id" in result:
                logger.info(f"发布草稿成功，publish_id: {result['publish_id']}")
                return result
            
            errcode = result.get("errcode", -1)
            errmsg = result.get("errmsg", "未知错误")
            raise WeChatAPIError(errcode, errmsg)
            
        except requests.RequestException as e:
            logger.error(f"发布草稿网络错误: {e}")
            raise WeChatNetworkError(str(e))
    
    def get_publish_status(self, publish_id: str) -> Dict:
        """查询发布状态
        
        Args:
            publish_id: 发布任务ID
                
        Returns:
            dict: 发布状态详情
        """
        if not publish_id:
            raise ValueError("publish_id 不能为空")
        
        token = self.get_access_token()
        url = f"{self.BASE_URL}/freepublish/get"
        
        data = {"publish_id": publish_id}
        
        try:
            response = self._request_with_retry(
                "POST",
                url,
                params={"access_token": token},
                json_data=data,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            result = response.json()
            
            if "errcode" in result and result["errcode"] != 0:
                raise WeChatAPIError(result["errcode"], result.get("errmsg", "未知错误"))
            
            logger.info(f"查询发布状态成功，publish_id: {publish_id}")
            return result
            
        except requests.RequestException as e:
            logger.error(f"查询发布状态网络错误: {e}")
            raise WeChatNetworkError(str(e))
    
    # ==================== 工具方法 ====================
    
    def test_connection(self) -> Dict:
        """测试API连接
        
        用于验证app_id和app_secret是否正确配置。
        
        Returns:
            dict: {
                "success": bool,
                "message": str,
                "token_preview": str (成功时),
                "error_code": int (失败时)
            }
        """
        try:
            token = self.get_access_token()
            
            # 显示token前10位用于确认
            token_preview = token[:10] + "..." if len(token) > 10 else token
            
            # 检查缓存状态
            cache_info = self._token_cache.get_info()
            
            return {
                "success": True,
                "message": "微信公众号API连接成功",
                "token_preview": token_preview,
                "app_id": self.app_id,
                "cache_info": cache_info
            }
            
        except WeChatAPIError as e:
            return {
                "success": False,
                "message": f"连接失败：{e.message}",
                "error_code": e.code,
                "original_error": e.original_msg
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接失败：{str(e)}",
                "error_code": -1
            }
    
    def get_token_status(self) -> Dict:
        """获取token状态
        
        Returns:
            dict: token缓存状态信息
        """
        cache_info = self._token_cache.get_info()
        
        if cache_info:
            expires_at = datetime.fromisoformat(cache_info["expires_at"])
            remaining_seconds = (expires_at - datetime.now()).total_seconds()
            
            return {
                "has_cache": True,
                "expires_at": expires_at.isoformat(),
                "remaining_seconds": max(0, remaining_seconds),
                "is_valid": remaining_seconds > self._token_cache.EXPIRE_MARGIN,
                "app_id": cache_info.get("app_id", ""),
                "created_at": cache_info.get("created_at", "")
            }
        
        return {
            "has_cache": False,
            "is_valid": False,
            "message": "无有效缓存，需要获取新token"
        }
    
    # ==================== 内部方法 ====================
    
    def _request_with_retry(
        self,
        method: str,
        url: str,
        params: Dict = None,
        json_data: Dict = None,
        files: Dict = None,
        timeout: int = None,
        retry_on_token_error: bool = True
    ) -> requests.Response:
        """带重试机制的请求方法
        
        Args:
            method: 请求方法（GET/POST）
            url: 请求URL
            params: URL参数
            json_data: JSON数据
            files: 上传文件
            timeout: 超时时间
            retry_on_token_error: token错误时是否重试
                
        Returns:
            requests.Response: 响应对象
        """
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT
        
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                # 检查调用频率（简单限制）
                self._check_rate_limit()
                
                # 发送请求
                if method.upper() == "GET":
                    response = requests.get(
                        url,
                        params=params,
                        timeout=timeout,
                        headers={"Accept": "application/json"}
                    )
                else:
                    if files:
                        response = requests.post(
                            url,
                            params=params,
                            files=files,
                            timeout=timeout
                        )
                    else:
                        # 关键：使用 ensure_ascii=False 保持中文字符原样
                        # 否则中文会被转义成 \uXXXX 导致长度大大增加
                        import json
                        json_str = json.dumps(json_data, ensure_ascii=False)
                        response = requests.post(
                            url,
                            params=params,
                            data=json_str.encode('utf-8'),
                            timeout=timeout,
                            headers={"Content-Type": "application/json; charset=utf-8"}
                        )
                
                # 记录调用时间
                self._last_call_time = time.time()
                self._call_count += 1
                
                # 检查响应
                if response.status_code != 200:
                    raise WeChatNetworkError(f"HTTP状态码错误：{response.status_code}")
                
                # 检查是否是token错误
                try:
                    data = response.json()
                    errcode = data.get("errcode", 0)
                    
                    if errcode in self.TOKEN_ERROR_CODES and retry_on_token_error:
                        logger.warning(f"Token错误（{errcode}），尝试刷新后重试...")
                        
                        # 刷新token
                        new_token = self.get_access_token(force_refresh=True)
                        
                        # 更新params中的token
                        if params and "access_token" in params:
                            params["access_token"] = new_token
                        
                        # 继续下一次重试
                        continue
                except json.JSONDecodeError:
                    pass
                
                return response
                
            except requests.Timeout:
                last_error = WeChatNetworkError(f"请求超时（{timeout}秒）")
                logger.warning(f"请求超时，尝试重试（{attempt + 1}/{self.MAX_RETRIES}）")
                
            except requests.ConnectionError as e:
                last_error = WeChatNetworkError(f"连接错误：{str(e)}")
                logger.warning(f"连接错误，尝试重试（{attempt + 1}/{self.MAX_RETRIES}）")
                
            except WeChatAPIError as e:
                # API错误不重试
                raise e
            
            # 重试延迟
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.RETRY_DELAY * (attempt + 1))
        
        # 所有重试都失败
        if last_error:
            raise last_error
        raise WeChatNetworkError("请求失败，已达到最大重试次数")
    
    def _check_rate_limit(self) -> None:
        """检查调用频率
        
        微信API有调用频率限制，这里做简单的检查。
        """
        # 微信API调用频率限制大约是每秒1次
        min_interval = 0.5  # 最小间隔500ms
        
        elapsed = time.time() - self._last_call_time
        if elapsed < min_interval and self._last_call_time > 0:
            sleep_time = min_interval - elapsed
            logger.debug(f"调用间隔过短，等待 {sleep_time:.2f} 秒")
            time.sleep(sleep_time)


# ==================== 工厂函数 ====================

def create_wechat_api(app_id: str = None, app_secret: str = None) -> WeChatAPI:
    """创建微信API实例
    
    Args:
        app_id: 微信AppID（可选，从settings获取）
        app_secret: 微信AppSecret（可选，从settings获取）
        
    Returns:
        WeChatAPI: 微信API实例
        
    Raises:
        ValueError: 配置不完整时抛出
    """
    # 如果未提供参数，从settings获取
    if not app_id or not app_secret:
        try:
            from config.settings import get_settings
            settings = get_settings()
            
            if not app_id:
                app_id = settings.WECHAT_APP_ID
            if not app_secret:
                app_secret = settings.WECHAT_APP_SECRET
            
            # 验证配置
            if not settings.has_wechat_config():
                raise ValueError(
                    "微信配置不完整。请在 .env 文件中设置：\n"
                    "WECHAT_APP_ID=your_app_id\n"
                    "WECHAT_APP_SECRET=your_app_secret"
                )
        except ImportError:
            raise ValueError("无法导入配置模块，请手动提供 app_id 和 app_secret")
    
    return WeChatAPI(app_id=app_id, app_secret=app_secret)


# ==================== 类型别名 ====================

# 文章数据类型
ArticleData = Dict[str, Union[str, int]]

# 草稿列表项类型
DraftItem = Dict[str, Any]

# API响应类型
APIResponse = Dict[str, Any]


# ==================== 导出 ====================

__all__ = [
    # 主类
    "WeChatAPI",
    
    # 异常类
    "WeChatAPIError",
    "WeChatNetworkError",
    "WeChatTokenExpiredError",
    
    # 缓存类
    "TokenCache",
    
    # 工厂函数
    "create_wechat_api",
    
    # 类型别名
    "ArticleData",
    "DraftItem",
    "APIResponse",
]