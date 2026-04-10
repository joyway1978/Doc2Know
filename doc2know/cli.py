"""命令行接口模块"""

import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import click

from .config import Config, ConfigError
from .parser import DocxParser
from .pdf_parser import PdfParser
from .analyzer import LLMAnalyzer
from .generator import MarkdownGenerator
from .indexer import Indexer


class DocumentProcessor:
    """文档处理器，整合parser/analyzer/generator/indexer"""

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
                click.echo(f"  成功 -> {result.get('output_file', 'N/A')}")
            else:
                stats["failed"] += 1
                click.echo(f"  失败: {result.get('error', '未知错误')}")

        # 更新索引
        click.echo("\n更新索引...")
        self.indexer.update_index()
        click.echo(f"索引已更新: {self.config.output_dir}/index.md")

        return stats

    def process_file(self, file_path: str) -> dict:
        """
        处理单个文件

        Args:
            file_path: 文件路径

        Returns:
            处理结果字典
        """
        result = {
            "file": file_path,
            "success": False,
            "output_file": None,
            "error": None,
        }

        try:
            # 1. 解析文档
            ext = Path(file_path).suffix.lower()
            if ext == '.pdf':
                parsed_content = self.pdf_parser.parse(file_path)
            else:
                parsed_content = self.docx_parser.parse(file_path)

            # 2. LLM分析
            analysis_result = self.analyzer.analyze(parsed_content)

            # 3. 生成Markdown
            output_file = self.generator.generate(analysis_result, file_path)

            result["success"] = True
            result["output_file"] = output_file

        except Exception as e:
            result["error"] = str(e)

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


if __name__ == "__main__":
    main()
