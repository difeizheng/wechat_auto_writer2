"""
数据模型定义
使用原生 SQLite 实现，简单可靠
定义文章、模板、配置等数据结构
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import json


@dataclass
class Article:
    """文章数据模型"""
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    digest: str = ""  # 摘要
    style: str = ""  # 风格（科普/故事/干货/互动）
    topic: str = ""  # 主题
    template_id: Optional[int] = None  # 关联模板
    ai_model: str = ""  # 使用的AI模型
    cover_image_path: str = ""  # 封面图路径（本地保存）
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    wechat_draft_id: str = ""  # 微信草稿ID
    wechat_media_id: str = ""  # 微信素材ID
    status: str = "draft"  # draft/uploaded/published
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "digest": self.digest,
            "style": self.style,
            "topic": self.topic,
            "template_id": self.template_id,
            "ai_model": self.ai_model,
            "cover_image_path": self.cover_image_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "wechat_draft_id": self.wechat_draft_id,
            "wechat_media_id": self.wechat_media_id,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            title=data.get("title", ""),
            content=data.get("content", ""),
            digest=data.get("digest", ""),
            style=data.get("style", ""),
            topic=data.get("topic", ""),
            template_id=data.get("template_id"),
            ai_model=data.get("ai_model", ""),
            cover_image_path=data.get("cover_image_path", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            wechat_draft_id=data.get("wechat_draft_id", ""),
            wechat_media_id=data.get("wechat_media_id", ""),
            status=data.get("status", "draft")
        )


@dataclass
class Template:
    """模板数据模型"""
    id: Optional[int] = None
    name: str = ""
    category: str = ""  # 分类
    prompt_template: str = ""  # Prompt模板
    style_config: str = ""  # 风格配置JSON
    created_at: Optional[datetime] = None
    is_active: bool = True
    
    def get_style_config_dict(self) -> dict:
        """获取风格配置字典"""
        if self.style_config:
            try:
                return json.loads(self.style_config)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_style_config_dict(self, config: dict):
        """设置风格配置"""
        self.style_config = json.dumps(config)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "prompt_template": self.prompt_template,
            "style_config": self.style_config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Template":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            category=data.get("category", ""),
            prompt_template=data.get("prompt_template", ""),
            style_config=data.get("style_config", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            is_active=bool(data.get("is_active", True))
        )


@dataclass
class ConfigItem:
    """配置数据模型"""
    key: str = ""
    value: str = ""
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConfigItem":
        """从字典创建"""
        return cls(
            key=data.get("key", ""),
            value=data.get("value", ""),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )


# 状态常量定义
class ArticleStatus:
    """文章状态常量"""
    DRAFT = "draft"  # 草稿
    UPLOADED = "uploaded"  # 已上传到微信
    PUBLISHED = "published"  # 已发布


class TemplateCategory:
    """模板分类常量"""
    SCIENCE = "科普"  # 科普文章
    STORY = "故事"  # 故事分享
    DRY_GOODS = "干货"  # 干货总结
    INTERACTIVE = "互动"  # 互动文章