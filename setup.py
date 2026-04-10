from setuptools import setup, find_packages

setup(
    name="doc2know",
    version="0.1.0",
    description="将Word文档自动转换为结构化Markdown知识库",
    author="待填",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "python-docx>=0.8.11",
        "openai>=1.0.0",
        "pyyaml>=6.0",
        "click>=8.0",
        "tenacity>=8.0",
    ],
    entry_points={
        "console_scripts": [
            "doc2know=doc2know.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
