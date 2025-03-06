import os
import re
import json
import traceback
import subprocess

from chat import Chat

class Deep(Chat):
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
                ret = subprocess.run(['python3', '-c', cmd['code']], capture_output=True)
                if ret.returncode == 0:
                    res = { "stdout": ret.stdout.decode('utf-8'), "exitcode": ret.returncode }
                else:
                    res = { "stderr": ret.stderr.decode('utf-8'), "exitcode": ret.returncode }
            elif cmd['name'] == 'bash':
                if 'code' not in cmd:
                    raise Exception("Invalid bash call format")
                ret = subprocess.run(cmd['code'], shell=True, capture_output=True)
                if ret.returncode == 0:
                    res = { "stdout": ret.stdout.decode('utf-8'), "exitcode": ret.returncode }
                else:
                    res = { "stderr": ret.stderr.decode('utf-8'), "exitcode": ret.returncode }
            cmd.update(res)
        return commands

    def chat(self, user:str, msg:str, history:dict[str, list], model:str, temperature:float=0.7, run:bool=False):
        """对话，会修改传入的历史记录"""
        try:
            history['history'].append({
                "role": "user", "content": msg,
                "metadata": { "user": user, "run": run, "deep": True }
            })
            response = self.client.chat.completions.create(
                model=model,
                messages=history['history'],
                temperature=temperature,
                stream=True
            )

            print(f"╭─  󱚣  {model}")
            result = self._render_response(response, len(history['snippet']))
            history['snippet'] += result['snippets']
            history['history'].append({
                "role": "assistant", "content": result['answer'],
                "metadata": { "model": model }
            })

            commands = self._check_parse(result['answer'])
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
                        print(f' -> stdout[ExitCode: 0]')
                        print(cmd['stdout'])
                    if 'stderr' in cmd:
                        print(f' -> stderr[ExitCode: {cmd["exitcode"]}]')
                        print(cmd['stderr'])
                print('╰─────────────')
                return 'exec', content, history
        except KeyboardInterrupt:
            print()
            print("╭─    中断")
            print("╰─  本轮对话已停止。")
            return 'finish', '', history