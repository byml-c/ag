import os
import re
import json
import traceback
import subprocess
from openai import OpenAI
from render import MDStreamRenderer

from chat import Chat

class Deep(Chat):
    def _render_response(self, response, history:dict[str, list]=None):
        if history is None:
            history = { "snippet": [], "history": [] }
        reasoning_content, answer_content = "", ""
        is_reasoning, is_answering = False, False

        with MDStreamRenderer(len(history['snippet'])) as markdown:
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
                    markdown.update(re.sub(r'\n+', '\n> ', delta.reasoning_content))
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
            history['snippet'] += markdown.code_list
        if is_reasoning or is_answering:
            print()
        history['history'].append({
            "role": "assistant",
            "content": answer_content
        })
        return history, reasoning_content
    
    def _check_parse(self, s:str):
        commands = []
        s = re.search(r'^(.*?)```(.*?)\n(.*)\n```(.*?)$', 
                      s.strip(), re.S)
        if s is None:
            return None
        s = s.groups()
        if len(s) == 4 and s[1] == 'json':
            try:
                cmd = json.loads(s[2])
                if type(cmd) is not list:
                    raise Exception("Invalid type")
                for c in cmd:
                    if type(c) is not dict:
                        raise Exception("Invalid type")
                    if "name" not in c:
                        raise Exception("Invalid format")
                    if c['name'] not in ['python', 'bash']:
                        raise Exception("Invalid name")
                    commands.append(c)
            except Exception as _:
                pass
        return commands if len(commands) > 0 else None
    
    def _exec(self, commands:list[dict]):
        for cmd in commands:
            res = None
            if cmd['name'] == 'python':
                if 'code' not in cmd:
                    raise Exception("Invalid Python call format")
                ret = subprocess.run(['python3', '-cmd', cmd['code']], capture_output=True)
                if ret.returncode == 0:
                    res = { "stdout": ret.stdout.decode('utf-8') }
                else:
                    res = { "stderr": ret.stderr.decode('utf-8') }
            elif cmd['name'] == 'bash':
                if 'code' not in cmd:
                    raise Exception("Invalid bash call format")
                ret = subprocess.run(cmd['code'], shell=True, capture_output=True)
                if ret.returncode == 0:
                    res = { "stdout": ret.stdout.decode('utf-8') }
                else:
                    res = { "stderr": ret.stderr.decode('utf-8') }
            cmd.update(res)
        return commands

    def chat(self, msg:str, history:dict[str, list], model:str, temperature:float=0.7):
        """对话"""
        try:
            history['history'].append({"role": "user", "content": msg})
            response = self.client.chat.completions.create(
                model=model,
                messages=history['history'],
                temperature=temperature,
                stream=True
            )

            print(f"╭─  󱚣  {model}")
            hist, _ = self._render_response(response, history)
            commands = self._check_parse(hist['history'][-1]['content'])
            if commands is None:
                print('╰─────────────')
                return 'finish', '', history
            else:
                # 解析出可执行代码
                print('├─ RUN')
                commands = self._exec(commands)
                content = json.dumps(commands, ensure_ascii=False)
                for cmd in commands:
                    print(f'[{cmd["name"]}] {cmd["code"]!r}', end='')
                    if 'stdout' in cmd:
                        print(f' -> stdout')
                        print(cmd['stdout'])
                    if 'stderr' in cmd:
                        print(f' -> stderr')
                        print(cmd['stderr'])
                print('╰─────────────')
                return 'exec', content, history
        except KeyboardInterrupt:
            print()
            print("╭─    中断")
            print("╰─  本轮对话已停止。")
            return 'finish', '', history