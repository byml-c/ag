# Shell-Agent

## Introduction

在终端中运行属于你自己的 AI Agent！

通过 OpenAI 格式的 API 服务，你可以在终端中运行自己的 AI Agent。

## Features

- AI 问答：支持多种大模型，并可以在对话时灵活切换
- 定义变量：可以定义常值变量和终端变量两种变量，在问答时可以调用变量（终端变量将在调用时执行）
- Markdown 渲染：通过设置终端样式，实现 Markdown 渲染。可渲染代码块、标题、列表等样式

## Screenshots
定义变量：
![运行示例](./img/OS.png)

解释命令：
![运行示例](./img/OS2.png)

## Requirements
- Linux 系统
- Python 3.10+

## Installation

1. 配置 Python 运行环境
2. 运行安装脚本 `bash install.sh`，根据提示完成安装

## Usage
- 直接输入问题，按下回车键，即可得到回答。
- 输入 `/help` 查看帮助信息。