#!/usr/bin/env python3
"""
测试大模型连接
"""
import os
import sys
from openai import OpenAI

# 加载配置
config_path = os.environ.get("DOCS2KNOW_CONFIG", "config.yaml")

# 手动设置配置（避免依赖yaml）
BASE_URL = "https://copilot.weibo.com/v1"
API_KEY = "sk-wecode-aigc_zhongwei9_weibo_tags-key"
MODEL = "wecode-agent-max"

def test_llm():
    """测试大模型连接"""
    print(f"正在连接大模型...")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Model: {MODEL}")
    print()

    try:
        # 创建客户端
        client = OpenAI(
            base_url=BASE_URL,
            api_key=API_KEY,
            timeout=60
        )

        # 发送测试问题
        question = "中国最长的河流是？"
        print(f"提问: {question}")
        print("-" * 40)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": question}
            ],
            stream=False
        )

        # 获取回答
        answer = response.choices[0].message.content
        print(f"回答: {answer}")
        print()
        print("✅ 大模型连接成功！")

    except Exception as e:
        print(f"❌ 连接失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_llm()
