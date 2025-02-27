#!/bin/env python
import os
import re
import sys
import json
import time
import traceback
import subprocess
from pathlib import Path
from openai import OpenAI
import argparse

from thirdparty.rich.markdown import Markdown
from thirdparty.rich.console import Console
from thirdparty.rich.style import Style
from thirdparty.rich.theme import Theme
from thirdparty.rich.text import Text
from thirdparty.rich.live import Live

# 导入 readline 模块，用于支持上下键选择历史记录
import readline

# 配置文件路径
ROOT_DIR = Path("/home/byml/projects/my-style/ai_agent")
CONFIG_FILE  = ROOT_DIR / "config.json"
HISTORY_FILE = ROOT_DIR / ".agdata" / "history.json"
VARS_FILE    = ROOT_DIR / ".agdata" / "vars.json"
SNAPS_DIR    = ROOT_DIR / ".agdata" / "snaps"


# 自定义主题
custom_theme = Theme({
    "markdown.block_quote": "#999999 on #1f1f1f",
    "markdown.block_quote_border": "#d75f00",
    "markdown.h1": "bold #1E90FF",
    "markdown.h2": "bold #00BFFF",
    "markdown.h3": "bold #87CEFA",
    "markdown.h4": "bold #87CEEB",
    "markdown.h5": "bold #E0FFFF",
    "markdown.h6": "#E0FFFF",
    "live.ellipsis": "#e6db74 on #272822"
})
console = Console(theme=custom_theme)

class MDStreamRenderer:
    def __init__(self, code_start:int):
        self.md = None
        self.live = None
        self.code_start = code_start
        self.code_list = []
        self.content = ""
    
    def __enter__(self):
        self._new()
        self.code_list = []
        return self
    
    def _new(self, text=''):
        if self.md is not None:
            self.live.__exit__(None, None, None)
        self.content = text
        self.live = Live(console=console, auto_refresh=False)
        self.live.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.live is None:
            return 
        self.live.__exit__(exc_type, exc_value, traceback)

    def _add_snap(self, lang, code):
        self.code_list.append({"lang": lang, "code": code})
        cid = self.code_start+len(self.code_list)-1
        console.print(Text(f'   snap {cid}  ', justify='right', style="#e6db74 on #272822"),
                      Text(f'', justify='right', style="#272822"), sep='')

    def _end(self):
        if self.md is not None and len(self.code_list) > 0:
            c = self.md.parsed[-1]
            if c.type == 'fence' and c.block:
                self._add_snap(c.info, c.content)

    def _update(self, edl:str=''):
        self.content += edl
        try:
            # 使用自定义主题的 Markdown
            self.md = Markdown(
                self.content, 
                code_theme="monokai",
                inline_code_lexer="text"
            )
            
            c = self.md.parsed[-1]
            if c.type == 'fence' and c.block:
                if len(self.md.parsed) > 1:
                    self.md.parsed.pop()
                    last_pose = self.content.rfind('```')
                    self.live.update(self.md, refresh=True)
                    self._new(self.content[last_pose:])
                else:
                    self.live.update(self.md, refresh=True)
            else:
                c = self.md.parsed[0]
                if c.type == 'fence' and c.block:
                    code_end = self.content.rfind('```')
                    if code_end != -1:
                        self._add_snap(c.info, c.content)
                        self._new(self.content[code_end+3:])
                else:
                    self.live.update(self.md, refresh=True)
                    if edl == '\n\n':
                        self._new()
                        console.print()
        except:
            self.live.update(Text(self.content), refresh=True)

    def update(self, chunk:str):
        chunk = re.sub(r"\n{2,}", "\n\n", chunk)
        length, i = len(chunk), 0
        while i < length:
            if chunk[i] == '\n':
                if i+1 < length and chunk[i+1] == '\n':
                    self._update('\n\n')
                    i = i+1
                else:
                    self._update('\n')
            else:
                self.content += chunk[i]
            i += 1
        if self.content != "":
            self._update()

class AIChat:
    def __init__(self):
        self.config = self.load_config()
        os.environ['all_proxy'] = ''
        os.environ['http_proxy'] = ''
        os.environ['https_proxy'] = ''
        self.client = OpenAI(
            api_key=self.config["api_key"],
            base_url=self.config["base_url"]
        )
        os.makedirs(ROOT_DIR / ".agdata", exist_ok=True)
        self.history = self.load_history()
        self.vars = self.load_vars()
        
        # 初始化系统提示
        if not any(msg["role"] == "system" for msg in self.history['history']):
            self.history['history'].insert(0, {
                "role": "system",
                "content": self.config["system_prompt"]
            })
    
    @staticmethod
    def load_config():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config = json.load(f)
            
        if config["api_key"] == "":
            print(f"请先配置API密钥: {CONFIG_FILE}")
            sys.exit(1)
        return config

    def load_history(self):
        """加载对话历史"""
        # if HISTORY_FILE.exists():
        #     with open(HISTORY_FILE, encoding="utf-8") as f:
        #         return json.load(f)
        return {
            'history': [],
            'snap': []
        }
    
    def load_vars(self):
        """加载变量"""
        if VARS_FILE.exists():
            with open(VARS_FILE, encoding="utf-8") as f:
                return json.load(f)
        return {
            "users": {},
            "bash": {}
        }
    
    def save_config(self):
        """保存配置"""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def save_history(self):
        """保存对话历史"""
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def save_vars(self):
        """保存变量"""
        with open(VARS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.vars, f, indent=2, ensure_ascii=False)

    def update_snap(self):
        os.makedirs(SNAPS_DIR, exist_ok=True)
        for sid in range(len(self.history['snap'])):
            with open(SNAPS_DIR / f"{sid}", "w", encoding="utf-8") as f:
                f.write(self.history['snap'][sid]['code'])

    def find_model(self, s:str):
        for model in self.config["models"]:
            if model["model"] == s:
                return model["model"]
            for alias in model["alias"]:
                if alias == s:
                    return model["model"]
        return None

    def chat(self, msg:str):
        """对话"""
        try:
            self.history['history'].append({"role": "user", "content": msg})
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=self.history['history'],
                temperature=self.config["temperature"],
                stream=True
            )

            print(f"╭─  󱚣  {self.config['model']}")
            reasoning_content = ""
            answer_content = ""
            is_reasoning, is_answering = False, False
            with MDStreamRenderer(len(self.history['snap'])) as markdown:
                for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    # 打印思考过程
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                        if delta.reasoning_content != "" and is_reasoning == False:
                            print("├─  󰟷  THINK", flush=True)
                            markdown.update('> ')
                            is_reasoning = True
                        markdown.update(delta.reasoning_content.replace('\n', '\n> '))
                        reasoning_content += delta.reasoning_content
                    else:
                        # 开始回复
                        if delta.content != "" and is_answering == False:
                            if is_reasoning:
                                markdown._new()
                                print()
                            print("├─  󰛩  ANSWER", flush=True)
                            is_answering = True
                        # 打印回复过程
                        markdown.update(delta.content)
                        answer_content += delta.content
                markdown._end()
                self.history['snap'] += markdown.code_list
                self.update_snap()
            if is_reasoning or is_answering:
                print()
            print('╰─────────────')
            self.history['history'].append({
                "role": "assistant",
                "content": answer_content
            })
        except KeyboardInterrupt:
            self.save_history()
            print()
            print("╭─    中断")
            print("╰─  本轮对话已停止。")
    
    def bash(self, cmd:str):
        start_time = time.time()
        result = subprocess.run(
            cmd, shell=True, check=True, text=True, capture_output=True)
        cost_time = int((time.time() - start_time) * 1000)
        return result.stdout.strip(), cost_time, result.returncode

    def short(self, s:str, l:int=30):
        """缩短字符串"""
        if len(s) > l:
            return s[:l-10] + " ... " + s[-10:]
        else:
            return s

    def command(self, cmd:str):
        if cmd[:6] == 'change':
            if cmd == 'change':
                print()
                print(f"╭─    修改模型（当前模型：{self.config['model']}）")
                for model in self.config["models"]:
                    print(f"│   {model['model']}: ", end="")
                    for alias in model["alias"]:
                        print(f"{alias} ", end="")
                    print()
                print("├─────────────")
                model = input("│   请输入模型或别名: ")
            else:
                model = cmd[7:]
            model = self.find_model(model)
            if model is not None:
                self.config["model"] = model
                self.save_config()
                print(f"╰─    成功切换到模型：{model}")
            else:
                print(f"╰─    模型不存在")
            return 'done'
        elif cmd in ['cls', 'clear']:
            os.system('clear')
            return 'done'
        elif cmd == 'forget':
            self.history['history'] = [self.history['history'][0]]
            self.history['snap'] = []
            print()
            print("╭─    清空历史")
            print("╰─  历史已清空。")
            return 'done'
        elif cmd in ['quit', 'exit', 'bye']:
            self.save_history()
            print()
            print("╭─    再见")
            print("╰─  历史已保存。")
            return 'exit'
        elif cmd[:4] == 'bash':
            print()
            print(f"╭─    终端命令")
            try:
                out, cost_time, returncode = self.bash(cmd[5:])
                print(out, end="")
                print(f"╰─    执行结束，  {cost_time} ms, return {returncode}")
            except KeyboardInterrupt:
                print(f"╰─    中断执行，  {cost_time} ms, return {returncode}")
            except Exception as e:
                print(f"╰─    执行出错：{e}")
            return 'done'
        elif cmd[:4] in ['varr', 'vart']:
            print()
            print(f"╭─    设置常值变量")
            try:
                cmd = cmd[5:].split(' ', 1)
                out, cost_time, returncode = self.bash(cmd[1:])
                self.vars["users"][cmd[0]] = out
                self.save_vars()
                print(f"├─  {cmd[0]} = \"{self.short(self.vars['users'][cmd[0]])}\"")
                print(f"╰─    设置成功，  {cost_time} ms, return {returncode}")
            except KeyboardInterrupt:
                print(f"╰─    中断执行，  {cost_time} ms, return {returncode}")
            except Exception as e:
                print(f"╰─    设置失败：{e}")
            return 'done'
        elif cmd[:4] in ['varc', 'varb']:
            print()
            print(f"╭─    设置终端变量")
            try:
                cmd = cmd[5:].split(' ', 1)
                self.vars["bash"][cmd[0]] = cmd[1]
                self.save_vars()
                print(f"├─  {cmd[0]} = \"{self.vars['bash'][cmd[0]]}\"")
                print(f"╰─    设置成功")
            except KeyboardInterrupt:
                print(f"╰─    中断设置")
            except Exception as e:
                print(f"╰─    设置失败：{e}")
            return 'done'
        elif cmd[:4] == 'show':
            user_print, bash_print = False, False
            def print_title(t:str):
                nonlocal user_print, bash_print
                if t == 'u' and not user_print:
                    print("├─    常值文本变量")
                    user_print = True
                if t == 'b' and not bash_print:
                    print("├─    终端命令变量")
                    bash_print = True
            print()
            print(f"╭─    变量列表")
            cmd = cmd[5:].strip()
            for k, v in self.vars["users"].items():
                if cmd == '' or re.match(cmd, k):
                    print_title('u')
                    print(f"│   {k:10} = {self.short(v)!r}")
            for k, v in self.vars["bash"].items():
                if cmd == '' or re.match(cmd, k):
                    print_title('b')
                    print(f"│   {k:10} = {v!r}")
            print("╰─────────────")
            return 'done'
        elif cmd[:4] == 'snap':
            print()
            print(f"╭─    代码列表")
            cmd = cmd[5:].strip()
            for sid in range(len(self.history['snap'])):
                snap = self.history['snap'][sid]
                if cmd == '' or snap['lang'] == cmd:
                    print(f"│   {sid:3} [{snap['lang']:10}]: {self.short(snap['code'])!r}")
            print("╰─────────────")
            return 'done'
        else:
            print()
            if cmd != 'help':
                print(f"╭─    未知命令 \"{cmd}\"")
                print(f"├─  󰘥  帮助")
            else:
                print("╭─  󰘥  帮助")
            print("├─  命令语法为 /+命令，变量在对话时可通过 {var_name} 引用")
            print("├─    控制命令")
            print("│   cls   : 清空屏幕，历史、变量均不会清空")
            print("│   forget: 清空历史，变量不会清空")
            print("│   change: 切换模型")
            print("│   snap  : 查看代码片段")
            print("│   help  : 查看帮助")
            print("│   exit  : 退出")
            print("├─    终端命令")
            print("│   bash <command>       : 结果将直接输出在对话框中")
            print("│   varr <name> <command>: 将终端命令运行结果保存在变量中")
            print("│   varc <name> <command>: 将终端命令直接保存在变量中")
            print("│   show <option:name>   : 打印变量，支持正则，无参数时打印所有变量")
            print("╰─────────────")
            return 'done'
    
    def prase(self, ipt:str):
        """解析输入"""
        def replace_var(match:re.Match):
            if match is None: return ''
            val = self.vars["users"].get(match.group(1))
            if val is not None:
                return val
            val = self.vars["bash"].get(match.group(1))
            if val is not None:
                return self.bash(val)[0]
            return match.group(0)
        # 替换变量
        ipt = re.sub(r"{(.*?)}", replace_var, ipt)
        return ipt

    def main(self):
        """执行对话"""
        try:
            user_name = os.getenv("USER")
            while True:
                user_input = input(f"\n╭─  󱋊 {user_name}\n╰─  ").strip()
                if len(user_input) > 0 and user_input[0] == '/':
                    ret = self.command(user_input[1:])
                    if ret == 'exit':
                        break
                else:
                    self.chat(self.prase(user_input))
        except KeyboardInterrupt:
            self.save_history()
            print()
            print("╭─    终止")
            print("╰─  退出程序")
        except Exception as _:
            self.save_history()
            print()
            print(f"╭─    错误")
            print(f"╰─  {traceback.format_exc()}")

def main():
    ai = AIChat()
    ai.main()
    return

if __name__ == "__main__":
    main()
