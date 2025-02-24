#!/home/byml/app/anaconda3/bin/python
import os
import re
import sys
import json
import time
import subprocess
from pathlib import Path
from openai import OpenAI, Transport

# 导入 readline 模块，用于支持上下键选择历史记录
if os.name == 'posix':
    import readline
elif os.name == 'nt':
    import pyreadline3 as readline

# 配置文件路径
ROOT_DIR = Path("/home/byml/projects/my-style/ai_agent")
CONFIG_FILE  = ROOT_DIR / "config.json"
HISTORY_FILE = ROOT_DIR / ".agdata" / "history.json"
VARS_FILE    = ROOT_DIR / ".agdata" / "vars.json"

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
        if not any(msg["role"] == "system" for msg in self.history):
            self.history.insert(0, {
                "role": "system",
                "content": self.config["system_prompt"]
            })

    @staticmethod
    def load_config():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config = json.load(f)
            
        if config["api_key"] == "your-api-key-here":
            print(f"请先配置API密钥: {CONFIG_FILE}")
            sys.exit(1)
            
        return config

    def load_history(self):
        """加载对话历史"""
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
        return []
    
    def load_vars(self):
        """加载变量"""
        if VARS_FILE.exists():
            with open(VARS_FILE, encoding="utf-8") as f:
                return json.load(f)
        return {}
    
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
            self.history.append({"role": "user", "content": msg})
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=self.history,
                temperature=self.config["temperature"],
                stream=True
            )

            print(f"╭─  󱚣  {self.config['model']}")
            reasoning_content = ""
            answer_content = ""
            is_reasoning, is_answering = False, False
            for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                # 打印思考过程
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                    if delta.reasoning_content != "" and is_reasoning == False:
                        print("├─  󰟷  THINK", flush=True)
                        is_reasoning = True
                    print(delta.reasoning_content, end="", flush=True)
                    reasoning_content += delta.reasoning_content
                else:
                    # 开始回复
                    if delta.content != "" and is_answering == False:
                        print("\n├─  󰛩  ANSWER", flush=True)
                        is_answering = True
                    # 打印回复过程
                    print(delta.content, end="", flush=True)
                    answer_content += delta.content
            print('\n╰─────────────')
            self.history.append({
                "role": "assistant",
                "content": answer_content
            })
        except KeyboardInterrupt:
            self.save_history()
            print()
            print("╭─    中断")
            print("╰─  本轮对话已停止。")
    
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
                self.history = [self.history[0]]
                print(f"╰─    成功切换到模型：{model}")
            else:
                print(f"╰─    模型不存在")
            return 'done'
        elif cmd == 'clear':
            self.history = [self.history[0]]
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
            print(f"╭─    Bash 命令")
            try:
                start_time = time.time()
                result = subprocess.run(
                    cmd[5:], shell=True, check=True, text=True, capture_output=True)
                cost_time = int((time.time() - start_time) * 1000)
                print(result.stdout, end="")
                print(f"╰─    执行结束，  {cost_time} ms, return {result.returncode}")
            except KeyboardInterrupt:
                print(f"╰─    中断执行，  {cost_time} ms, return {result.returncode}")
            except Exception as e:
                print(f"╰─    执行出错：{e}")
            return 'done'
        elif cmd[:3] == 'var':
            print()
            print(f"╭─    变量设置")
            try:
                cmd = cmd[4:].split(' ', 1)
                start_time = time.time()
                result = subprocess.run(
                    cmd[1:], shell=True, check=True, text=True, capture_output=True)
                cost_time = int((time.time() - start_time) * 1000)
                self.vars[cmd[0]] = result.stdout.strip()
                self.save_vars()
                print(f"├─  {cmd[0]} = \"{self.vars[cmd[0]]}\"")
                print(f"╰─    设置成功，  {cost_time} ms, return {result.returncode}")
            except KeyboardInterrupt:
                print(f"╰─    中断执行，  {cost_time} ms, return {result.returncode}")
            except Exception as e:
                print(f"╰─    设置失败：{e}")
            return 'done'
        elif cmd[:4] == 'show':
            print()
            print(f"╭─    变量列表")
            cmd = cmd[5:].strip()
            if cmd == '':
                for k, v in self.vars.items():
                    print(f"├─  {k} = \"{v}\"")
            else:
                for k, v in self.vars.items():
                    if re.match(cmd, k):
                        print(f"├─  {k} = \"{v}\"")
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
            print("│   clear : 清空历史，变量不会清空")
            print("│   change: 切换模型")
            print("│   help  : 查看帮助")
            print("│   exit  : 退出")
            print("├─    Bash 命令")
            print("│   bash <command>      : 结果将直接输出在对话框中")
            print("│   var <name> <command>: 将结果保存在变量中")
            print("│   show <option:name>  : 打印变量，支持正则，无参数时打印所有变量")
            print("╰─────────────")
            return 'done'
    
    def prase(self, ipt:str):
        """解析输入"""
        # 替换变量
        for k, v in self.vars.items():
            ipt = ipt.replace(f"{{{k}}}", v)
        return ipt

    def main(self):
        """执行对话"""
        try:
            if os.name == 'posix':
                user_name = os.getenv("USER")
            elif os.name == 'nt':
                user_name = os.getenv("USERNAME")
            while True:
                user_input = input(f"\n╭─  󱋊 {user_name}\n╰─  ").strip()
                if user_input[0] == '/':
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
        except Exception as e:
            print()
            print(f"╭─    错误")
            print(f"╰─  {str(e)}")
            self.save_history()

def main():
    ai = AIChat()
    ai.main()

if __name__ == "__main__":
    main()
