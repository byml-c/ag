#!/bin/env python
from _global import *

import os
import re
import sys
import json
import time
import argparse
import readline
import traceback
from pathlib import Path

from chat import Chat
from deep import Deep
import execute

def complete_cd(text, state):
    # 仅当输入以 "cd " 开头时触发补全
    ipt = readline.get_line_buffer()
    if ipt.startswith("cd "):
        # 获取当前目录下所有匹配的文件夹
        pth = os.path.abspath('/'.join(ipt[3:].split('/')[:-1]))
        dirs = [d + "/" for d in os.listdir(pth) 
                if os.path.isdir(os.path.join(pth, d)) and d.startswith(text)]
        return dirs[state] if state < len(dirs) else None
    return None

readline.set_completer(complete_cd)
readline.parse_and_bind("tab: complete")

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
        self.history['history'].insert(0, {
            "role": "system",
            "content": self.config["deep_prompt"] \
                if self.config["deep"] else self.config["chat_prompt"]
        })
    
    @staticmethod
    def load_config():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config = json.load(f)
            
        if config["api_key"] == "":
            print(f"请先配置API密钥: {CONFIG_FILE}")
            sys.exit(1)
        return config

    def load_history(self, not_ok:bool=True):
        """加载对话历史"""
        if self.hist_path.exists():
            with open(self.hist_path, encoding="utf-8") as f:
                return json.load(f)
        if not_ok:
            return {
                'history': [],
                'snippet': []
            }
        else:
            raise FileNotFoundError("History file is not exist.")
    
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
        with open(self.hist_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def archive_history(self):
        '''归档存储历史记录'''
        if len(self.history['history']) <= 1: return 
        os.makedirs(HISTORY_DIR, exist_ok=True)
        if self.hist_path == HISTORY_FILE:
            time_str = time.strftime(HISTORY_FORMAT, time.localtime())
            self.hist_path = HISTORY_DIR / f"{time_str}.json"
        self.save_history()
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
    
    def save_vars(self):
        """保存变量"""
        with open(VARS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.vars, f, indent=2, ensure_ascii=False)

    def update_snippet(self):
        os.makedirs(SNIPPETS_DIR, exist_ok=True)
        for sid in range(len(self.history['snippet'])):
            os.environ[f'S{sid}'] = str(SNIPPETS_DIR / f"{sid}")
            with open(SNIPPETS_DIR / f"{sid}", "w", encoding="utf-8") as f:
                f.write(self.history['snippet'][sid]['code'])

    def find_model(self, s:str):
        for model in self.config["models"]:
            if model["model"] == s:
                return model["model"]
            for alias in model["alias"]:
                if alias == s:
                    return model["model"]
        return None
    
    def get_user(self):
        return os.getenv("USER")

    def short(self, s:str, l:int=25):
        """缩短字符串"""
        if len(s) > l:
            return s[:l-10] + "..." + s[-10:]
        else:
            return s

    def terminal(self, cmd:str=None, single:bool=True):
        '''终端命令模式'''
        while True:
            if not single:
                try:
                    print(f"╭─    {os.getcwd()}")
                    cmd = self.input_lines(f"├─   $ ").strip()
                except KeyboardInterrupt:
                    print()
                    print("╰─  󰈆  退出终端模式")
                    return 'done'
            splitted = cmd.split(' ', 1) if ' ' in cmd else (cmd, '')
            exec, args = splitted[0].strip(), splitted[1].strip()
            
            match exec:
                case 'help':
                    config_status = "默认" if CONFIG_FILE.name == "config.json" \
                        else CONFIG_FILE.name.lstrip("config-").rstrip(".json")
                    print("╭─  󰘥  帮助（模式：{}，模型：{}，配置：{}）".format(
                        "终端模式" if not single else ("深度对话" if self.config['deep'] else "普通对话"),
                        self.config['model'], config_status))
                    print("├─  控制模式语法为 /+命令，终端模式可直接使用命令")
                    print("├─    变量使用")
                    print("│   {<var_name>}        : 使用常值变量或终端命令变量")
                    print("│   {$S<sid>[, $S<sid>]}: 使用代码片段（其中符合深度思考格式的片段会自动执行）")
                    print("├─    控制模式")
                    print("│   new    : 保存对话并开启新对话")
                    print("│   cls    : 清空屏幕，历史、变量均不会清空")
                    print("│   load   : 加载历史")
                    print("│   forget : 清空历史，变量不会清空")
                    print("│   change : 切换模型")
                    print("│   chat   : 切换到{}".format("普通对话" if self.config['deep'] else "深度对话"))
                    print("│   func   : 查看自定义函数说明")
                    print("│   bash   : 进入终端命令模式")
                    print("│   parse  : 解析输入为实际调用输入")
                    print("│   help   : 查看帮助")
                    print("│   exit   : 退出对话")
                    print("│   show <option:name>       : 打印变量，支持正则，无参数时打印所有变量")
                    print("│   snippet <option:language>: 查看代码片段，支持正则，无参数时打印所有变量")
                    print("├─    终端模式")
                    print("│   cd <path>            : 进入对应路径并将工作目录切换至该路径")
                    print("│   setr <name> <command>: 将终端命令运行结果保存在变量中")
                    print("│   setb <name> <command>: 将终端命令直接保存在变量中")
                    print("│   <command>            : 执行终端命令（包括控制模式命令），可直接获取返回值")
                    print("│   exit                 : 退出终端模式，返回对话模式")
                    print("╰─────────────")
                
                case 'new':
                    self.archive_history()
                    self.hist_path = HISTORY_FILE
                    self.history['history'] = [self.history['history'][0]]
                    self.history['snippet'] = []
                    self.terminal('clear', True)
                
                case 'cls' | 'clear':
                    os.system('clear')
                
                case 'load':
                    print()
                    print("╭─    历史记录")
                    hist_files:list[Path] = []
                    if HISTORY_DIR.exists():
                        hist_files = [
                            (i.stat().st_mtime, i) for i in list(HISTORY_DIR.iterdir())
                        ]
                        hist_files.sort(key=lambda x:x[0], reverse=True)
                    for hid in range(len(hist_files)):
                        print(f"│   {hid:3}: [{hist_files[hid][1].name.replace('.json', '')}] ", end="")
                        with open(hist_files[hid][1], encoding="utf-8") as f:
                            hist = json.load(f)
                            if len(hist['history']) > 1:
                                print(f"{self.short(hist['history'][1]['content'])!r}", end='')
                        print()
                    print("├─────────────")
                    hist = input("│   请输入历史记录编号: ")
                    try:
                        hist = int(hist)
                        if hist >= 0 and hist < len(hist_files):
                            self.hist_path:Path = hist_files[hist][1]
                            self.history = self.load_history(False)
                            print(f"├─    成功切换到历史记录：{self.hist_path.name.replace('.json', '')}")
                            record = input("├─  是否需要打印历史记录？[y/n]: ").lower()
                            if record == 'y':
                                self.terminal('clear', True)
                                _, result = self.chat._render_history(self.history)
                                self.history['snippet'] = result
                            else:
                                print(f"╰─────────────")
                            self.update_snippet()
                        else:
                            raise Exception("Records is not exist.")
                    except:
                        print(f"╰─    历史记录不存在")
                
                case 'forget':
                    self.history['history'] = [self.history['history'][0]]
                    self.history['snippet'] = []
                    print()
                    print("╭─    清空历史")
                    print("╰─  历史已清空。")
                
                case 'change':
                    if args == '':
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
                        model = args
                    model = self.find_model(model)
                    if model is not None:
                        self.config["model"] = model
                        self.save_config()
                        print(f"╰─    成功切换到模型：{model}")
                    else:
                        print(f"╰─    模型不存在")
                
                case 'chat' | 'deep':
                    print()
                    print(f"╭─    切换对话模式")
                    if cmd[4:].strip() == '1':
                        self.config['deep'][1] = True
                    elif cmd[4:].strip() == '0':
                        self.config['deep'] = False
                    else:
                        self.config['deep'] = not self.config['deep']
                    self.save_config()
                    print(f"╰─  已切换到{'深度对话' if self.config['deep'] else '普通对话'}")
                
                case 'show':
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
                    for k, v in self.vars["users"].items():
                        if args == '' or re.match(args, k):
                            print_title('u')
                            content = self.short(v) if args == '' else v
                            print(f"│   {k:10} = {content!r}")
                    for k, v in self.vars["bash"].items():
                        if args == '' or re.match(args, k):
                            print_title('b')
                            print(f"│   {k:10} = {v!r}")
                    print("╰─────────────")
                
                case 'func':
                    print()
                    print(f"╭─    自定义函数")
                    print(f"├─  调用方法：@函数名(参数1, 参数2, ...)")
                    print(f"├─────────────")
                    for func in execute.func_description:
                        if args == '' or re.match(args, func['name']):
                            params = []
                            for p in func['para']:
                                params.append(f"<{p[0]}: {p[1]}>")
                            params = ', '.join(params)
                            icon = func.get('icon', ' ')
                            des = self.short(func['des']) if args == '' else func['des']
                            print(f"│   {icon}{func['name']}({params}): {des}")
                    print("╰─────────────")
                
                case 'snippet':
                    print()
                    print(f"╭─    代码列表")
                    for sid in range(len(self.history['snippet'])):
                        snippet = self.history['snippet'][sid]
                        if args == '' or re.match(args, snippet['lang']):
                            content = self.short(snippet['code']) if args == '' else snippet['code']
                            print(f"│   $S{sid:<3} [{snippet['lang']:10}]: {content!r}")
                    print("╰─────────────")
                
                case 'exit' | 'bye' | 'quit':
                    if single:
                        return 'exit'
                    else:
                        break
                
                case 'cd':
                    try:
                        if args == '':
                            os.chdir(os.path.expanduser("~"))
                        else:
                            os.chdir(os.path.expanduser(args))
                    except (FileNotFoundError, NotADirectoryError):
                        print("╰─    路径不存在！")
                
                case 'setr' | 'sett':
                    print()
                    print(f"╭─    设置常值变量")
                    try:
                        if ' ' not in args:
                            name, command = args, ''
                        else:
                            name, command = args.split(' ', 1)
                        
                        if command == '':
                            if self.vars["users"].get(name) is not None:
                                self.vars["users"].pop(name)
                                self.save_vars()
                                print(f"╰─    变量 {name} 删除成功！")
                            else:
                                raise ValueError(f"变量 {name} 不存在")
                        else:
                            out, err, cost_time, returncode = execute.bash(command)
                            
                            exists = None
                            if name in self.vars["users"]:
                                exists = ("users", "常值")
                            elif name in self.vars["bash"]:
                                exists = ("bash", "终端")
                            if exists is not None:
                                valid = input(f"├─    {exists[1]}变量 {name} 已存在，是否覆盖？[y/n]: ")
                                if valid.lower() == 'y':
                                    self.vars[exists[0]].pop(name)
                                else: raise KeyboardInterrupt
                            
                            if out == '':
                                raise ValueError("命令执行结果为空")
                            else:
                                self.vars["users"][name] = out
                                self.save_vars()
                                print(f"├─  {name} = {self.short(self.vars['users'][name])!r}")
                                print(f"╰─    设置成功，  {cost_time} ms, return {returncode}")
                    except KeyboardInterrupt:
                        print(f"╰─    中断执行，  {cost_time} ms, return {returncode}")
                    except Exception as e:
                        print(f"╰─    设置失败：{traceback.format_exc()}")
                
                case 'setb' | 'setc':
                    print()
                    print(f"╭─    设置终端变量")
                    try:
                        if ' ' not in args:
                            name, command = args, ''
                        else:
                            name, command = args.split(' ', 1)
                        
                        if command == '':
                            if self.vars["bash"].get(name) is not None:
                                self.vars["bash"].pop(name)
                                self.save_vars()
                                print(f"╰─    变量 {name} 删除成功！")
                            else:
                                raise ValueError(f"变量 {name} 不存在")
                        else:
                            exists = None
                            if name in self.vars["users"]:
                                exists = ("users", "常值")
                            elif name in self.vars["bash"]:
                                exists = ("bash", "终端")
                            if exists is not None:
                                valid = input(f"├─    {exists[1]}变量 {name} 已存在，是否覆盖？[y/n]: ")
                                if valid.lower() == 'y':
                                    self.vars[exists[0]].pop(name)
                                else: raise KeyboardInterrupt
                            
                            self.vars["bash"][name] = command
                            self.save_vars()
                            print(f"├─  {name} = {self.vars['bash'][name]!r}")
                            print(f"╰─    设置成功")
                    except KeyboardInterrupt:
                        print(f"╰─    中断设置")
                    except Exception as e:
                        print(f"╰─    设置失败：{e}")
                
                case 'parse':
                    print()
                    print(f"╭─    解析输入")
                    try:
                        print(f"├─  {self.prase(args)}")
                        print(f"╰─    解析结束")
                    except Exception as e:
                        print(f"╰─    解析失败：{traceback.format_exc()}")
                
                case _:
                    out, err, cost_time, returncode = execute.bash(cmd)
                    print(out)
                    if returncode != 0:
                        print(f"├─────────────")
                        print(err)
                        print(f"╰─    执行失败，  {cost_time} ms, return {returncode}")
                    else:
                        print(f"╰─    执行结束，  {cost_time} ms, return {returncode}")
            
            if single: break
        return 'done'

    def command(self, cmd:str):
        '''控制命令模式'''
        try:
            if cmd.startswith('bash'):
                if cmd == 'bash':
                    return self.terminal(None, False)
                else:
                    return self.terminal(cmd[4:], True)
            else:
                return self.terminal(cmd, True)
        except:
            print(f"╭─    终端模式错误")
            print(f"╰─  {traceback.format_exc()}")
    
    def prase(self, ipt:str):
        """解析输入"""
        def replace_var(match:re.Match):
            if match is None: return ''
            key = match.group(1).strip()
            # 常值变量
            val = self.vars["users"].get(key)
            if val is not None:
                return val
            # 终端命令变量
            val = self.vars["bash"].get(key)
            if val is not None:
                return self.bash(val)[0]
            # 代码片段
            if re.match(r"(\$S\d+[, ]*?)+", key):
                sid_list, outputs = re.findall(r"\$S(\d+)", key), ''''''
                for sid in sid_list:
                    if int(sid) >= len(self.history['snippet']):
                        continue
                    s = self.history['snippet'][int(sid)]
                    if s['lang'] == 'json':
                        cmds = execute.check_parse(f"```json\n{s['code']}\n```")
                        if cmds is not None:
                            opt, _ = execute.parse_and_exec(cmds)
                            outputs += '\n ------ Run Result ------ \n'+opt
                        else:
                            outputs += '\n ------ json ------ \n'+s['code']
                    else:
                        outputs += '\n ------ '+s['lang']+' ------ \n'+s['code']
                return outputs
        # 替换变量
        ipt = re.sub(r"{(.*?)}", replace_var, ipt)
        
        def replace_func(match:re.Match):
            try:
                name, para = match.group(1), match.group(2)
                if execute.__dict__.get(name) is not None:
                    return execute.__dict__[name](execute.parse_para(para))
                else:
                    raise AttributeError(f"Unknown function: {name}")
            except:
                return match.group(0)
        # 处理函数
        ipt = re.sub(r"@(.*?)\(([\s\S]*?)\)", replace_func, ipt, re.S)
        return ipt

    @staticmethod
    def input_lines(prompt):
        content = ''
        line = input(prompt).rstrip()
        while True:
            if line.endswith('\\'):
                content += line[:-1] + '\n'
            else: break
            line = input().rstrip()
        return content + line

    def main(self):
        """执行对话"""
        try:
            user_name = self.get_user()
            while True:
                icon = '󰧑 ' if self.config['deep'] else '󱋊 '
                print(f'\n╭─  {icon} {user_name}', flush=True)
                user_input = self.input_lines(f"╰─  ").strip()
                if len(user_input) > 0 and user_input[0] == '/':
                    ret = self.command(user_input[1:].strip())
                    if ret == 'exit':
                        break
                else:
                    if self.config['deep']:
                        self.history['history'][0]['content'] = self.config['deep_prompt']
                        msg = self.prase(user_input)
                        for round in range(20):
                            status, cmd, _ = self.deep.chat(
                                user=user_name,
                                msg=msg,
                                history=self.history,
                                model=self.config["model"],
                                run=round > 0
                            )
                            self.update_snippet()
                            if status == 'exec':
                                msg = cmd
                            else: break
                    else:
                        self.history['history'][0]['content'] = self.config['chat_prompt']
                        status, _ = self.chat.chat(
                            user=user_name,
                            msg=self.prase(user_input),
                            history=self.history,
                            model=self.config["model"]
                        )
                        self.update_snippet()
        except KeyboardInterrupt:
            print()
            print("╭─  󰈆  终止")
            print("╰─  退出程序")
        except Exception as _:
            print()
            print(f"╭─    错误")
            print(f"╰─  {traceback.format_exc()}")
        
        self.archive_history()

def main():
    ai = Agent()
    ai.main()
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent")
    parser.add_argument("-l", "--local", action='store_true', help="Use local config (\"config-local.json\").")
    parser.add_argument("-c", "--config", type=str, help="Use custom config file.")
    args = parser.parse_args()
    
    if args.local:
        CONFIG_FILE = CONFIG_FILE.parent / CONFIG_FILE.name.replace(".json", "-local.json")
    if args.config is not None:
        CONFIG_FILE = Path(args.config)
    main()
