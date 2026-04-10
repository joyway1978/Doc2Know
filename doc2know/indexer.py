"""索引管理模块"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml


class Indexer:
    """索引管理器，负责扫描主题文件并生成/更新索引"""

    def __init__(self, output_dir: str):
        """
        初始化索引器

        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.topics_dir = self.output_dir / "topics"
        self.index_file = self.output_dir / "index.md"

    def update_index(self) -> None:
        """
        扫描output_dir/topics/下的所有markdown文件
        提取信息并更新output_dir/index.md
        """
        # 确保topics目录存在
        if not self.topics_dir.exists():
            self.topics_dir.mkdir(parents=True, exist_ok=True)

        # 扫描所有主题文件
        new_topics = self._scan_topics()

        # 读取现有索引（如果存在）
        existing_topics = self._load_existing_index()

        # 合并新旧信息（增量更新）
        merged_topics = self._merge_topics(existing_topics, new_topics)

        # 生成索引内容
        index_content = self._generate_index_content(merged_topics)

        # 写入索引文件
        self.index_file.write_text(index_content, encoding="utf-8")

    def _scan_topics(self) -> List[Dict]:
        """
        扫描所有主题文件，返回信息列表

        Returns:
            主题信息列表，每个主题包含title, summary, tags, updated_at, file_path
        """
        topics = []

        if not self.topics_dir.exists():
            return topics

        # 扫描所有markdown文件
        for md_file in sorted(self.topics_dir.glob("*.md")):
            if md_file.name == "index.md":
                continue

            metadata = self._extract_metadata(str(md_file))
            if metadata:
                # 添加文件路径信息（相对路径）
                metadata["file_path"] = f"topics/{md_file.name}"
                # 添加文件修改时间
                stat = md_file.stat()
                metadata["updated_at"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                topics.append(metadata)

        return topics

    def _extract_metadata(self, file_path: str) -> Optional[Dict]:
        """
        从markdown文件提取YAML frontmatter

        Args:
            file_path: markdown文件路径

        Returns:
            包含title, summary, tags的字典，如果提取失败返回None
        """
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except (IOError, UnicodeDecodeError):
            return None

        # 解析YAML frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

        if frontmatter_match:
            try:
                yaml_content = frontmatter_match.group(1)
                data = yaml.safe_load(yaml_content) or {}

                return {
                    "title": data.get("title", ""),
                    "summary": data.get("summary", ""),
                    "tags": data.get("tags", []),
                }
            except yaml.YAMLError:
                pass

        # 如果没有frontmatter，尝试从内容中提取
        return self._extract_metadata_from_content(content)

    def _extract_metadata_from_content(self, content: str) -> Dict:
        """
        从markdown内容中提取元数据（无frontmatter时备用）

        Args:
            content: markdown内容

        Returns:
            包含title, summary, tags的字典
        """
        lines = content.strip().split('\n')

        title = ""
        summary = ""
        tags = []

        # 提取标题（第一个#开头的行）
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                title = line[2:].strip()
                break
            elif line.startswith('## '):
                title = line[3:].strip()
                break

        # 如果没有找到标题，使用第一行非空内容
        if not title:
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    title = line[:50]
                    break

        # 提取摘要（第一个非标题段落）
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 20:
                summary = line[:100] if len(line) > 100 else line
                break

        # 尝试从内容中提取标签（查找标签模式）
        tag_patterns = [
            r'#([\u4e00-\u9fa5a-zA-Z0-9_]+)',  # #标签 格式
            r'标签[：:]\s*([^\n]+)',  # 标签：xxx 格式
        ]
        for pattern in tag_patterns:
            matches = re.findall(pattern, content)
            if matches:
                if isinstance(matches[0], tuple):
                    tags = [t.strip() for t in matches[0].split(',') if t.strip()]
                else:
                    tags = matches[:5]
                break

        return {
            "title": title or "未命名文档",
            "summary": summary or "暂无摘要",
            "tags": tags,
        }

    def _load_existing_index(self) -> List[Dict]:
        """
        读取现有index.md中的主题信息

        Returns:
            现有主题信息列表
        """
        if not self.index_file.exists():
            return []

        try:
            content = self.index_file.read_text(encoding="utf-8")
        except (IOError, UnicodeDecodeError):
            return []

        topics = []

        # 解析表格内容
        # 格式: | [标题](路径) | 摘要 | 标签 | 日期 |
        lines = content.split('\n')
        in_table = False

        for line in lines:
            line = line.strip()

            # 跳过表头分隔行
            if line.startswith('|---'):
                in_table = True
                continue

            # 跳过表头
            if line.startswith('| 文档') or line.startswith('|文档'):
                in_table = True
                continue

            # 解析表格行
            if in_table and line.startswith('|'):
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if len(cells) >= 4:
                    # 解析文档链接 [标题](路径)
                    doc_cell = cells[0]
                    link_match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', doc_cell)

                    if link_match:
                        title = link_match.group(1)
                        file_path = link_match.group(2)
                        summary = cells[1]
                        tags_str = cells[2]
                        updated_at = cells[3]

                        # 解析标签
                        tags = [t.strip() for t in tags_str.split(',') if t.strip()]

                        topics.append({
                            "title": title,
                            "file_path": file_path,
                            "summary": summary,
                            "tags": tags,
                            "updated_at": updated_at,
                        })

        return topics

    def _merge_topics(self, existing: List[Dict], new: List[Dict]) -> List[Dict]:
        """
        合并现有索引和新扫描的主题信息

        Args:
            existing: 现有索引中的主题列表
            new: 新扫描的主题列表

        Returns:
            合并后的主题列表
        """
        # 以文件路径为键建立索引
        topic_map: Dict[str, Dict] = {}

        # 先添加现有主题
        for topic in existing:
            file_path = topic.get("file_path", "")
            if file_path:
                topic_map[file_path] = topic

        # 合并新主题（新主题覆盖旧主题）
        for topic in new:
            file_path = topic.get("file_path", "")
            if file_path:
                topic_map[file_path] = topic

        # 转换回列表并按标题排序
        merged = list(topic_map.values())
        merged.sort(key=lambda x: x.get("title", ""))

        return merged

    def _generate_index_content(self, topics: List[Dict]) -> str:
        """
        生成索引文件内容

        Args:
            topics: 主题信息列表

        Returns:
            索引文件内容（markdown格式）
        """
        lines = [
            "# 知识库索引",
            "",
            f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> 共 {len(topics)} 篇文档",
            "",
            "| 文档 | 摘要 | 标签 | 更新时间 |",
            "|------|------|------|----------|",
        ]

        for topic in topics:
            title = topic.get("title", "未命名")
            file_path = topic.get("file_path", "")
            summary = topic.get("summary", "")
            tags = topic.get("tags", [])
            updated_at = topic.get("updated_at", "")

            # 格式化标签
            tags_str = ", ".join(tags) if tags else "-"

            # 截断摘要（如果太长）
            if len(summary) > 50:
                summary = summary[:47] + "..."

            # 转义表格中的管道符
            title = title.replace('|', '\\|')
            summary = summary.replace('|', '\\|')
            tags_str = tags_str.replace('|', '\\|')

            lines.append(f"| [{title}]({file_path}) | {summary} | {tags_str} | {updated_at} |")

        # 如果没有文档，添加提示
        if not topics:
            lines.append("| - | 暂无文档 | - | - |")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*本索引由 Doc2Know 自动生成*")
        lines.append("")

        return "\n".join(lines)


def update_index(output_dir: str) -> None:
    """
    便捷函数：更新索引

    Args:
        output_dir: 输出目录路径
    """
    indexer = Indexer(output_dir)
    indexer.update_index()
