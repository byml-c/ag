# My-Shell-AI-Agent

## Introduction

在终端中运行属于你自己的 AI Agent！

通过 OpenAI 格式的 API 服务，你可以在终端中运行自己的 AI Agent，实现实时问答。


## Installation

1. 选择合适的大模型服务商，或自己部署 Ollama 等本地服务。
2. 安装如下软件/软件包：
    - Python
    - OpenAI 包
    - pyreadline3 包（仅限 Windows 系统）
3. 修改 `template_config.json` 中的 `api_key` 和 `base_url` 为你的 API Key 和 API Base URL。并改名为 `config.json`。
4. 给予运行权限 `sudo chmod +x ai.py`。
5. 直接运行 `./ai.py`。

## Usage
- 直接输入问题，按下回车键，即可得到回答。
- 输入 `/help` 查看帮助信息。