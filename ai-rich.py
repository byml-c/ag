#!/home/byml/app/anaconda3/bin/python
import os
import sys
import json
import argparse
from pathlib import Path
from openai import OpenAI

import time
from rich.console import Console
from rich.markdown import Markdown
from rich import box
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.theme import Theme

# 配置文件路径
CONFIG_DIR = Path("/home/byml/projects/my-style/ai_agent")
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"

# 初始化控制台
console = Console(
    force_terminal=True,
    height=100,
    theme=Theme({
    # "markdown.block_quote": "#949494 on #eeeeee",
    "markdown.block_quote": "#949494 on #1f1f1f",
}))

class StreamingMarkdown:
    def __init__(self):
        self.content = ""
        self.live = None
        self.markdown = None

    def __enter__(self):
        self.live = Live(console=console, refresh_per_second=15, vertical_overflow="visible")
        self.live.__enter__()
        return self

    def update(self, chunk):
        self.content += chunk
        try:
            # 尝试解析为 Markdown
            self.markdown = Markdown(self.content, code_theme="monokai")
            self.live.update(self._wrap_panel(self.markdown))
        except:
            # 降级处理为普通文本
            self.live.update(Text(self.content))

    def _wrap_panel(self, content):
        """包装对话气泡样式"""
        return Panel(
            content,
            title=f" 󱚣  {ai.config['model']}",
            title_align="left",
            expand=True,
            height=None,
        )

    def __exit__(self, *args):
        self.live.__exit__(*args)
        # 最终渲染一次完整 Markdown
        # console.print(self._wrap_panel(Markdown(self.content)))

class AIChat:
    def __init__(self):
        self.config = self.load_config()
        self.client = OpenAI(
            api_key=self.config["api_key"],
            base_url=self.config["base_url"]
        )
        self.history = self.load_history()
        
        # 初始化系统提示
        if not any(msg["role"] == "system" for msg in self.history):
            self.history.insert(0, {
                "role": "system",
                "content": self.config["system_prompt"]
            })

    @staticmethod
    def load_config():
        with open(CONFIG_FILE) as f:
            config = json.load(f)
            
        if config["api_key"] == "your-api-key-here":
            print(f"请先配置API密钥: {CONFIG_FILE}")
            sys.exit(1)
            
        return config

    def load_history(self):
        """加载对话历史"""
        # if HISTORY_FILE.exists():
        #     with open(HISTORY_FILE) as f:
        #         return json.load(f)
        return []

    def save_history(self):
        """保存对话历史"""
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history[-self.config["max_history"]*2:], f, indent=2, ensure_ascii=False)

    def chat(self):
        """执行对话"""
        def icon(s:str):
            return s.encode('utf-16', 'surrogatepass').decode('utf-16')

        try:
            user_name = os.getenv("USER")
            # 交互模式
            while True:
                user_input = console.input(f"\n╭─  󱋊 {user_name}\n╰─  ")
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    self.save_history()
                    console.print(f"\n╭─  {icon('\uebbc')} Bye\n╰─  history saved.")
                    break
                if user_input.lower() == 'clear':
                    self.history = [h for h in self.history if h["role"] == "system"]
                    console.print(f"\n╭─  {icon('\uf1f8 ')}Clean\n╰─  history cleaned.")
                    continue
                
                self.history.append({"role": "user", "content": user_input})
                
                with StreamingMarkdown() as streamer:
                    response = self.client.chat.completions.create(
                        model=self.config["model"],
                        messages=self.history,
                        temperature=self.config["temperature"],
                        stream=True
                    )
                    # def unit_test(l1, l2):
                    #     class chunk:
                    #         def __init__(self, t):
                    #             class choice:
                    #                 def __init__(self, t):
                    #                     class content:
                    #                         def __init__(self):
                    #                             self.content = '# test\n'
                    #                     class reasoning_content:
                    #                         def __init__(self):
                    #                             self.reasoning_content = 'test'*50
                    #                     if t == 1:
                    #                         self.delta = reasoning_content()
                    #                     else:
                    #                         self.delta = content()
                    #             self.choices = [choice(t)]
                    #     for _ in range(l1):
                    #         time.sleep(0.4)
                    #         yield chunk(1)
                    #     for _ in range(l2):
                    #         time.sleep(0.4)
                    #         yield chunk(2)
                    # response = unit_test(20, 20)

                    streamer.update(f"> 󰟷 **THINK**\n> ")
                    reasoning_content = ""
                    answer_content = ""
                    is_answering = False
                    for chunk in response:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        # 打印思考过程
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                            streamer.update(delta.reasoning_content.replace('\n', '\n>'))
                            reasoning_content += delta.reasoning_content
                        else:
                            # 开始回复
                            if delta.content != "" and is_answering == False:
                                streamer.update(f"\n")
                                is_answering = True
                            # 打印回复过程
                            streamer.update(delta.content)
                            answer_content += delta.content
                console.print()
                self.history.append({
                    "role": "assistant",
                    "content": answer_content
                })
                
        except KeyboardInterrupt:
            self.save_history()
            console.print(f"\n╭─    Bye\n╰─  history saved.")
        except Exception as e:
            console.print(f"\n╭─    Error\n╰─  {str(e)}")
            self.save_history()

# 初始化 AIChat
ai = AIChat()
def main():
    ai.chat()

if __name__ == "__main__":
    main()