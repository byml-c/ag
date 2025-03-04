#!/bin/env python
import os
import re
import sys
import json
import time
import argparse
import readline
import traceback
import subprocess
from pathlib import Path

from chat import Chat
from deep import Deep

# 配置文件路径
ROOT_DIR = Path(r"D:\\Programming\\ag")
CONFIG_FILE = ROOT_DIR / "config.json"
VARS_FILE = ROOT_DIR / ".agdata" / "vars.json"
HISTORY_DIR = ROOT_DIR / ".agdata" / "history"
HISTORY_FILE = ROOT_DIR / ".agdata" / "history.json"
SNIPPETS_DIR = ROOT_DIR / ".agdata" / "snippets"


class Agent:
    def __init__(self):
        self.config = self.load_config()
        os.makedirs(ROOT_DIR / ".agdata", exist_ok=True)
        self.hist_path = HISTORY_FILE
        self.history = self.load_history()
        self.vars = self.load_vars()
        self.chat = Chat(self.config["api_key"], self.config["base_url"])
        self.deep = Deep(self.config["api_key"], self.config["base_url"])

        # 初始化系统提示
        if not any(msg["role"] == "system" for msg in self.history["history"]):
            self.history["history"].insert(
                0, {"role": "system", "content": self.config["system_prompt"]}
            )

    @staticmethod
    def load_config():
        with open(CONFIG_FILE, encoding="gbk") as f:
            config = json.load(f)

        if config["api_key"] == "":
            print(f"请先配置API密钥: {CONFIG_FILE}")
            sys.exit(1)
        return config

    def load_history(self, not_ok: bool = True):
        """加载对话历史"""
        if self.hist_path.exists():
            with open(self.hist_path, encoding="gbk") as f:
                return json.load(f)
        if not_ok:
            return {"history": [], "snippet": []}
        else:
            raise FileNotFoundError("History file is not exist.")

    def load_vars(self):
        """加载变量"""
        if VARS_FILE.exists():
            with open(VARS_FILE, encoding="gbk") as f:
                return json.load(f)
        return {"users": {}, "bash": {}}

    def save_config(self):
        """保存配置"""
        with open(CONFIG_FILE, "w", encoding="gbk") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def save_history(self):
        """保存对话历史"""
        os.makedirs(HISTORY_DIR, exist_ok=True)
        with open(self.hist_path, "w", encoding="gbk") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def save_vars(self):
        """保存变量"""
        with open(VARS_FILE, "w", encoding="gbk") as f:
            json.dump(self.vars, f, indent=2, ensure_ascii=False)

    def update_snippet(self):
        os.makedirs(SNIPPETS_DIR, exist_ok=True)
        for sid in range(len(self.history["snippet"])):
            os.environ[f"S{sid}"] = str(SNIPPETS_DIR / f"{sid}")
            with open(SNIPPETS_DIR / f"{sid}", "w", encoding="utf-8") as f:
                f.write(self.history["snippet"][sid]["code"])

    def find_model(self, s: str):
        for model in self.config["models"]:
            if model["model"] == s:
                return model["model"]
            for alias in model["alias"]:
                if alias == s:
                    return model["model"]
        return None

    def get_user(self):
        return os.getenv("USER")

    def bash(self, cmd: str):
        start_time = time.time()
        import re

        cmd = re.sub(r"\$(.*) ?", r"%\1% ", cmd)
        # print("DEBUG: ", cmd)
        try:
            result = subprocess.run(
                cmd, shell=True, check=True, text=True, capture_output=True
            )
        finally:
            cost_time = int((time.time() - start_time) * 1000)
            return result.stdout.strip(), cost_time, result.returncode

    def short(self, s: str, l: int = 30):
        """缩短字符串"""
        if len(s) > l:
            return s[: l - 10] + " ... " + s[-10:]
        else:
            return s

    def command(self, cmd: str):
        if cmd[:6] == "change":
            if cmd == "change":
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
            return "done"
        elif cmd in ["cls", "clear"]:
            os.system("clear")
            return "done"
        elif cmd == "forget":
            self.history["history"] = [self.history["history"][0]]
            self.history["snippet"] = []
            print()
            print("╭─    清空历史")
            print("╰─  历史已清空。")
            return "done"
        elif cmd in ["quit", "exit", "bye"]:
            self.save_history()
            print()
            print("╭─    再见")
            print("╰─  历史已保存。")
            return "exit"
        elif cmd == "load":
            print()
            print("╭─    历史记录")
            hist_files: list[Path] = []
            if HISTORY_DIR.exists():
                hist_files = list(HISTORY_DIR.iterdir())
            for hid in range(len(hist_files)):
                print(
                    f"│   {hid:3}: [{hist_files[hid].name.replace('.json', '')}] ",
                    end="",
                )
                with open(hist_files[hid], encoding="gbk") as f:
                    hist = json.load(f)
                    if len(hist["history"]) > 1:
                        print(self.short(hist["history"][1]["content"]), end="")
                print()
            print("├─────────────")
            hist = input("│   请输入历史记录编号: ")
            try:
                hist = int(hist)
                if hist >= 0 and hist < len(hist_files):
                    self.hist_path = hist_files[hist]
                    self.history = self.load_history(False)
                    print(
                        f"├─    成功切换到历史记录：{hist_files[hist].name.replace('.json', '')}"
                    )
                    record = input("├─  是否需要打印历史记录？[y/n]: ").lower()
                    if record == "y":
                        self.command("clear")
                        self.chat._render_history(self.history)
                    else:
                        print(f"╰─────────────")
                    self.update_snippet()
                else:
                    raise Exception("Records is not exist.")
            except:
                print(f"╰─    历史记录不存在")
            return "done"
        elif cmd[:4] == "bash":
            print()
            print(f"╭─    终端命令")
            try:
                out, cost_time, returncode = self.bash(cmd[5:])
                print(out)
                print(f"╰─    执行结束，  {cost_time} ms, return {returncode}")
            except KeyboardInterrupt:
                print(f"╰─    中断执行，  {cost_time} ms, return {returncode}")
            except Exception as e:
                print(f"╰─    执行出错：{e}")
            return "done"
        elif cmd[:4] in ["varr", "vart"]:
            print()
            print(f"╭─    设置常值变量")
            try:
                cmd = cmd[5:].split(" ", 1)
                out, cost_time, returncode = self.bash(cmd[1:])
                self.vars["users"][cmd[0]] = out
                self.save_vars()
                print(f"├─  {cmd[0]} = \"{self.short(self.vars['users'][cmd[0]])}\"")
                print(f"╰─    设置成功，  {cost_time} ms, return {returncode}")
            except KeyboardInterrupt:
                print(f"╰─    中断执行，  {cost_time} ms, return {returncode}")
            except Exception as e:
                print(f"╰─    设置失败：{e}")
            return "done"
        elif cmd[:4] in ["varc", "varb"]:
            print()
            print(f"╭─    设置终端变量")
            try:
                cmd = cmd[5:].split(" ", 1)
                self.vars["bash"][cmd[0]] = cmd[1]
                self.save_vars()
                print(f"├─  {cmd[0]} = \"{self.vars['bash'][cmd[0]]}\"")
                print(f"╰─    设置成功")
            except KeyboardInterrupt:
                print(f"╰─    中断设置")
            except Exception as e:
                print(f"╰─    设置失败：{e}")
            return "done"
        elif cmd[:4] == "show":
            user_print, bash_print = False, False

            def print_title(t: str):
                nonlocal user_print, bash_print
                if t == "u" and not user_print:
                    print("├─    常值文本变量")
                    user_print = True
                if t == "b" and not bash_print:
                    print("├─    终端命令变量")
                    bash_print = True

            print()
            print(f"╭─    变量列表")
            cmd = cmd[5:].strip()
            for k, v in self.vars["users"].items():
                if cmd == "" or re.match(cmd, k):
                    print_title("u")
                    print(f"│   {k:10} = {self.short(v)!r}")
            for k, v in self.vars["bash"].items():
                if cmd == "" or re.match(cmd, k):
                    print_title("b")
                    print(f"│   {k:10} = {v!r}")
            print("╰─────────────")
            return "done"
        elif cmd[:4] == "snippet":
            print()
            print(f"╭─    代码列表")
            cmd = cmd[5:].strip()
            for sid in range(len(self.history["snippet"])):
                snippet = self.history["snippet"][sid]
                if cmd == "" or snippet["lang"] == cmd:
                    print(
                        f"│   $S{sid:<3} [{snippet['lang']:10}]: {self.short(snippet['code'])!r}"
                    )
            print("╰─────────────")
            return "done"
        else:
            print()
            if cmd != "help":
                print(f'╭─    未知命令 "{cmd}"')
                print(f"├─  󰘥  帮助")
            else:
                print("╭─  󰘥  帮助")
            print("├─  命令语法为 /+命令，变量在对话时可通过 {var_name} 引用")
            print("├─    控制命令")
            print("│   cls   : 清空屏幕，历史、变量均不会清空")
            print("│   forget: 清空历史，变量不会清空")
            print("│   load  : 加载历史")
            print("│   change: 切换模型")
            print("│   snippet  : 查看代码片段")
            print("│   help  : 查看帮助")
            print("│   exit  : 退出")
            print("├─    终端命令")
            print("│   bash <command>       : 结果将直接输出在对话框中")
            print("│   varr <name> <command>: 将终端命令运行结果保存在变量中")
            print("│   varc <name> <command>: 将终端命令直接保存在变量中")
            print("│   show <option:name>   : 打印变量，支持正则，无参数时打印所有变量")
            print("╰─────────────")
            return "done"

    def prase(self, ipt: str):
        """解析输入"""

        def replace_var(match: re.Match):
            if match is None:
                return ""
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

    @staticmethod
    def input_lines(prompt):
        content = ""
        print(prompt, end="")
        while True:
            line = input()
            if line.strip().endswith("\\"):
                content += line[:-1] + "\n"
            else:
                break
        return content + line

    def main(self):
        """执行对话"""
        try:
            user_name = self.get_user()
            while True:
                user_input = self.input_lines(f"\n╭─  󱋊 {user_name}\n╰─  ").strip()
                if len(user_input) > 0 and user_input[0] == "/":
                    ret = self.command(user_input[1:])
                    if ret == "exit":
                        break
                else:
                    self.deep_solve = True
                    if self.deep_solve:
                        self.history["history"][0][
                            "content"
                        ] = """
你是一个智能助手，拥有调用工具的能力，可以帮助用户解决遇到的问题。

当你需要调用工具时，你需要**只以 JSON 格式输出一个数组**，数组中的每个元素是一个字典，取值为以下两种：
1. `{"name": "python", "code": ""}` 表示调用 Python 执行代码，`code` 为 Python 代码字符串。
2. `{"name": "bash", "code": ""}` 表示调用 Bash 执行代码，`code` 为 Bash 代码字符串。
如果执行成功，你将会在下一次输入时得到调用代码的 stdout 结果，否则，你将收到 stderr 的结果。

比如：
用户提问：请介绍一下我的 Python 版本。
你的输出：
```json
[{"name": "bash", "code": "python3 --version"}]
```
用户返回：[{"name": "bash", "code": "python3 --version", "stdout": "Python 3.12.7\n"}]

然后，你可以正常回答用户的问题。
注意，只有在你以 ```json ... ``` 格式输出时，才会调用工具。否则，你并不会收到调用工具的结果。
所以，当你希望调用工具时，**请不要有任何其他的输出和提示**。

你需要合理思考，灵活运用工具，帮助用户解决遇到的问题！
"""

                        msg = self.prase(user_input)
                        for _ in range(20):
                            status, cmd, _ = self.deep.chat(
                                msg=msg,
                                history=self.history,
                                model=self.config["model"],
                            )
                            if status == "exec":
                                msg = cmd
                            else:
                                break
                    else:
                        status, _ = self.chat.chat(
                            msg=self.prase(user_input),
                            history=self.history,
                            model=self.config["model"],
                        )
        except KeyboardInterrupt:
            print()
            print("╭─    终止")
            print("╰─  退出程序")
        except Exception as _:
            print()
            print(f"╭─    错误")
            print(f"╰─  {traceback.format_exc()}")
        if len(self.history["history"]) > 1:
            if self.hist_path == HISTORY_FILE:
                time_str = time.strftime(r"%Y-%m-%d_%H-%M-%S", time.localtime())
                self.hist_path = HISTORY_DIR / f"{time_str}.json"
                os.remove(HISTORY_FILE)
            self.save_history()


def main():
    ai = Agent()
    ai.main()
    return


if __name__ == "__main__":
    main()
