"""Markdown生成模块"""

import os
import re
from datetime import datetime
from typing import Dict, Any, List


class MarkdownGenerator:
    """Markdown文件生成器，将LLM分析结果转换为Markdown格式"""

    def __init__(self, output_dir: str):
        """
        初始化Markdown生成器

        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = output_dir
        self.topics_dir = os.path.join(output_dir, "topics")

    def generate(self, analysis_result: Dict[str, Any], source_file: str) -> str:
        """
        生成Markdown文件

        Args:
            analysis_result: LLM分析结果（title, summary, tags, sections）
            source_file: 原始文档路径

        Returns:
            生成的文件路径
        """
        # 确保输出目录存在
        os.makedirs(self.topics_dir, exist_ok=True)

        # 获取标题并生成slug
        title = analysis_result.get("title", "未命名文档")
        slug = self._to_slug(title)

        # 确定最终文件名（处理冲突）
        filepath = self._resolve_filepath(slug)

        # 生成内容
        frontmatter = self._generate_frontmatter(analysis_result, source_file)
        content = self._generate_content(analysis_result.get("sections", []))

        # 写入文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter)
            f.write(content)

        return filepath

    def _to_slug(self, title: str) -> str:
        """
        将标题转换为slug格式（文件名）

        Args:
            title: 文档标题

        Returns:
            slug格式的字符串
        """
        if not title:
            return "untitled"

        # 转换为小写
        slug = title.lower()

        # 将中文字符转换为拼音（简化处理：保留中文字符，后续可扩展）
        # 这里先使用通用的slug化方法

        # 替换空格和特殊字符为连字符
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)

        # 移除首尾连字符
        slug = slug.strip("-")

        # 限制长度
        if len(slug) > 50:
            slug = slug[:50].rsplit("-", 1)[0]

        return slug or "untitled"

    def _resolve_filepath(self, slug: str) -> str:
        """
        确定最终文件路径（覆盖模式）

        Args:
            slug: 基础slug

        Returns:
            完整的文件路径
        """
        filepath = os.path.join(self.topics_dir, f"{slug}.md")
        return filepath

    def _generate_frontmatter(self, result: Dict[str, Any], source: str) -> str:
        """
        生成YAML frontmatter

        Args:
            result: 分析结果字典
            source: 原始文件路径

        Returns:
            YAML frontmatter字符串
        """
        title = result.get("title", "未命名文档")
        summary = result.get("summary", "")
        tags = result.get("tags", [])
        generated_at = datetime.now().isoformat()

        # 转义特殊字符
        title = title.replace('"', '\\"')
        summary = summary.replace('"', '\\"')

        # 构建YAML
        lines = [
            "---",
            f'title: "{title}"',
            f'summary: "{summary}"',
        ]

        # 处理tags列表
        if tags:
            tags_str = ", ".join(f'"{tag}"' for tag in tags)
            lines.append(f"tags: [{tags_str}]")
        else:
            lines.append("tags: []")

        lines.extend([
            f'source: "{source}"',
            f'generated_at: "{generated_at}"',
            "---",
            "",
        ])

        return "\n".join(lines)

    def _generate_content(self, sections: List[Dict]) -> str:
        """
        生成正文内容

        Args:
            sections: 章节列表

        Returns:
            Markdown格式的内容字符串
        """
        if not sections:
            return ""

        lines = []

        for section in sections:
            # 一级标题
            heading = section.get("heading", "")
            if heading:
                lines.append(f"# {heading}")
                lines.append("")

            # 处理子章节
            subsections = section.get("subsections", [])
            for subsection in subsections:
                sub_heading = subsection.get("heading", "")
                sub_content = subsection.get("content", "")

                if sub_heading:
                    lines.append(f"## {sub_heading}")
                    lines.append("")

                if sub_content:
                    lines.append(sub_content)
                    lines.append("")

        return "\n".join(lines)


def generate_markdown(analysis_result: Dict[str, Any], source_file: str, output_dir: str) -> str:
    """
    便捷函数：生成Markdown文件

    Args:
        analysis_result: LLM分析结果
        source_file: 原始文档路径
        output_dir: 输出目录

    Returns:
        生成的文件路径
    """
    generator = MarkdownGenerator(output_dir)
    return generator.generate(analysis_result, source_file)
