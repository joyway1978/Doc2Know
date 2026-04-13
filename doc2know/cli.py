"""命令行接口模块"""

import logging
import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import click

from .config import Config, ConfigError
from .parser import DocxParser
from .pdf_parser import PdfParser
from .analyzer import LLMAnalyzer
from .generator import MarkdownGenerator
from .indexer import Indexer
from .splitter import DocumentSplitter, SplitStrategy, SplitResult

import asyncio


class DocumentProcessor:
    """文档处理器，整合parser/splitter/generator/indexer"""

    def __init__(self, config: Config):
        """
        初始化文档处理器

        Args:
            config: 配置对象
        """
        self.config = config
        self.docx_parser = DocxParser()
        self.pdf_parser = PdfParser()
        self.analyzer = LLMAnalyzer(config)
        self.generator = MarkdownGenerator(config.output_dir)
        self.indexer = Indexer(config.output_dir)
        # 初始化文档拆分器
        strategy = SplitStrategy(config.split_strategy)
        self.splitter = DocumentSplitter(config, strategy)

    def process_all(self) -> dict:
        """
        处理所有文档

        Returns:
            处理统计信息字典
        """
        raw_dir = Path(self.config.raw_dir)

        # 扫描所有支持的文件类型
        docx_files = list(raw_dir.glob("*.docx"))
        docx_files.extend(raw_dir.glob("*.doc"))
        docx_files.extend(raw_dir.glob("*.pdf"))

        if not docx_files:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "files": [],
            }

        stats = {
            "total": len(docx_files),
            "success": 0,
            "failed": 0,
            "files": [],
        }

        click.echo(f"\n发现 {len(docx_files)} 个文档待处理\n")

        for i, file_path in enumerate(docx_files, 1):
            file_type = "PDF" if file_path.suffix.lower() == '.pdf' else "Word"
            click.echo(f"[{i}/{len(docx_files)}] [{file_type}] 处理: {file_path.name}")

            result = self.process_file(str(file_path))
            stats["files"].append(result)

            if result["success"]:
                stats["success"] += 1
                output_files = result.get('output_files', [])
                if output_files:
                    click.echo(f"  成功 -> 生成 {len(output_files)} 个文件:")
                    for f in output_files[:3]:  # 最多显示3个
                        click.echo(f"    - {Path(f).name}")
                    if len(output_files) > 3:
                        click.echo(f"    ... 还有 {len(output_files) - 3} 个文件")
                version_dir = result.get('version_dir')
                if version_dir:
                    click.echo(f"  版本目录: {version_dir}")
                warnings = result.get('warnings', [])
                for warning in warnings:
                    click.echo(f"  警告: {warning}")
            else:
                stats["failed"] += 1
                error_msg = result.get('error', '未知错误')
                click.echo(f"  失败: {error_msg}")

        # 更新索引
        click.echo("\n更新索引...")
        self.indexer.update_index()
        click.echo(f"索引已更新: {self.config.output_dir}/index.md")

        return stats

    def process_file(self, file_path: str) -> dict:
        """
        处理单个文件（使用智能拆分）

        Args:
            file_path: 文件路径

        Returns:
            处理结果字典
        """
        result = {
            "file": file_path,
            "success": False,
            "output_files": [],
            "version_dir": None,
            "categories": [],
            "error": None,
            "warnings": [],
        }

        try:
            # 1. 解析文档
            ext = Path(file_path).suffix.lower()
            if ext == '.pdf':
                parsed_content = self.pdf_parser.parse(file_path)
            else:
                parsed_content = self.docx_parser.parse(file_path)

            # 添加源文件信息
            parsed_content["source_file"] = file_path

            # 2. 智能拆分文档（三阶段分析）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                split_result = loop.run_until_complete(
                    self.splitter.split_document(parsed_content)
                )
            finally:
                loop.close()

            # 3. 处理结果
            result["success"] = len(split_result.files) > 0
            result["output_files"] = split_result.files
            result["version_dir"] = split_result.version_dir
            result["categories"] = split_result.categories

            # 收集警告信息
            if split_result.errors:
                result["warnings"] = split_result.errors
                # 如果有错误但仍有文件生成，视为部分成功
                if split_result.files:
                    result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            logger = logging.getLogger(__name__)
            logger.error(f"处理文件失败: {file_path}, 错误: {e}", exc_info=True)

        return result


@click.command()
@click.option(
    "--config",
    "-c",
    default="config.yaml",
    help="配置文件路径",
    show_default=True,
)
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    help="监听目录变化（持续监控raw_docs变化）",
)
@click.version_option(version="0.1.0", prog_name="doc2know")
def main(config: str, watch: bool):
    """
    Doc2Know - 将Word文档转换为结构化知识库

    基本用法:

        doc2know                    # 使用默认配置

        doc2know --config prod.yaml # 指定配置

        doc2know --watch            # 监听模式
    """
    # 显示欢迎信息
    click.echo("=" * 50)
    click.echo("Doc2Know - Word文档转结构化知识库")
    click.echo("=" * 50)

    # 加载配置
    try:
        cfg = Config(config)
        click.echo(f"配置加载成功: {config}")
        click.echo(f"  输入目录: {cfg.raw_dir}")
        click.echo(f"  输出目录: {cfg.output_dir}")
        click.echo(f"  LLM模型: {cfg.model}")
    except ConfigError as e:
        click.echo(f"配置错误: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"加载配置失败: {e}", err=True)
        sys.exit(1)

    # 创建处理器
    processor = DocumentProcessor(cfg)

    if watch:
        # 监听模式
        click.echo("\n进入监听模式，按 Ctrl+C 停止")
        click.echo(f"监控目录: {cfg.raw_dir}\n")

        processed_files = set()

        try:
            while True:
                # 扫描新文件
                raw_dir = Path(cfg.raw_dir)
                current_files = set(
                    str(p) for p in raw_dir.glob("*.docx")
                ) | set(str(p) for p in raw_dir.glob("*.doc")) | set(str(p) for p in raw_dir.glob("*.pdf"))

                new_files = current_files - processed_files

                if new_files:
                    click.echo(f"\n发现 {len(new_files)} 个新文件")
                    for file_path in new_files:
                        file_type = "PDF" if Path(file_path).suffix.lower() == '.pdf' else "Word"
                        click.echo(f"\n[{file_type}] 处理: {Path(file_path).name}")
                        result = processor.process_file(file_path)

                        if result["success"]:
                            click.echo(f"  成功 -> {result.get('output_file', 'N/A')}")
                            processor.indexer.update_index()
                        else:
                            click.echo(
                                f"  失败: {result.get('error', '未知错误')}",
                                err=True,
                            )

                    processed_files.update(new_files)
                    click.echo("\n等待新文件...")

                time.sleep(2)  # 每2秒检查一次

        except KeyboardInterrupt:
            click.echo("\n\n监听已停止")
            click.echo(f"共处理 {len(processed_files)} 个文件")

    else:
        # 单次处理模式
        stats = processor.process_all()

        # 显示统计信息
        click.echo("\n" + "=" * 50)
        click.echo("处理完成!")
        click.echo(f"  总计: {stats['total']} 个文件")
        click.echo(f"  成功: {stats['success']} 个")
        click.echo(f"  失败: {stats['failed']} 个")
        click.echo("=" * 50)

        if stats["failed"] > 0:
            sys.exit(1)


@click.command()
@click.option(
    "--config",
    "-c",
    default="config.yaml",
    help="配置文件路径",
    show_default=True,
)
@click.option(
    "--days",
    "-d",
    default=30,
    help="保留最近N天的版本",
    show_default=True,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="预览将要删除的目录，但不实际删除",
)
def cleanup(config: str, days: int, dry_run: bool):
    """
    清理旧版本目录

    删除指定天数之前的版本目录，保留最近N天的版本。
    默认保留最近30天。

    示例:

        doc2know cleanup              # 清理30天前的版本

        doc2know cleanup --days 7     # 只保留最近7天

        doc2know cleanup --dry-run    # 预览将要删除的目录
    """
    # 加载配置
    try:
        cfg = Config(config)
    except ConfigError as e:
        click.echo(f"配置错误: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"加载配置失败: {e}", err=True)
        sys.exit(1)

    output_dir = Path(cfg.output_dir)
    if not output_dir.exists():
        click.echo(f"输出目录不存在: {output_dir}")
        return

    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days)
    click.echo(f"清理 {days} 天前的版本 (截止: {cutoff_date.strftime('%Y-%m-%d')})")
    click.echo(f"输出目录: {output_dir}")
    click.echo("")

    # 查找版本目录
    version_dirs = []
    for item in output_dir.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            # 尝试解析目录名作为日期 (格式: YYYY-MM-DD-HHMM)
            try:
                dir_date = datetime.strptime(item.name, "%Y-%m-%d-%H%M")
                version_dirs.append((item, dir_date))
            except ValueError:
                # 不是版本目录，跳过
                pass

    # 按日期排序
    version_dirs.sort(key=lambda x: x[1], reverse=True)

    # 保留最近N天的版本
    dirs_to_keep = []
    dirs_to_delete = []

    for dir_path, dir_date in version_dirs:
        if dir_date >= cutoff_date:
            dirs_to_keep.append((dir_path, dir_date))
        else:
            dirs_to_delete.append((dir_path, dir_date))

    # 显示结果
    click.echo(f"找到 {len(version_dirs)} 个版本目录")
    click.echo(f"  保留: {len(dirs_to_keep)} 个")
    click.echo(f"  删除: {len(dirs_to_delete)} 个")
    click.echo("")

    if not dirs_to_delete:
        click.echo("没有需要清理的目录")
        return

    # 显示要删除的目录
    if dry_run:
        click.echo("【预览模式】以下目录将被删除:")
        for dir_path, dir_date in dirs_to_delete:
            click.echo(f"  - {dir_path.name} ({dir_date.strftime('%Y-%m-%d %H:%M')})")
        click.echo("")
        click.echo("使用 --dry-run 预览，未实际删除")
        return

    # 确认删除
    click.echo("以下目录将被删除:")
    for dir_path, dir_date in dirs_to_delete:
        click.echo(f"  - {dir_path.name} ({dir_date.strftime('%Y-%m-%d %H:%M')})")
    click.echo("")

    if not click.confirm("确认删除以上目录?"):
        click.echo("已取消")
        return

    # 执行删除
    deleted_count = 0
    error_count = 0

    for dir_path, dir_date in dirs_to_delete:
        try:
            shutil.rmtree(dir_path)
            click.echo(f"  已删除: {dir_path.name}")
            deleted_count += 1
        except Exception as e:
            click.echo(f"  删除失败: {dir_path.name} - {e}", err=True)
            error_count += 1

    click.echo("")
    click.echo(f"清理完成: 删除 {deleted_count} 个目录")
    if error_count > 0:
        click.echo(f"失败: {error_count} 个目录")


if __name__ == "__main__":
    main()
