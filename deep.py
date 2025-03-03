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


# with open('config.json') as f:
#     config = json.load(f)
# os.environ['all_proxy'] = ''
# os.environ['http_proxy'] = ''
# os.environ['https_proxy'] = ''
# client = OpenAI(
#     api_key=config["api_key"],
#     base_url=config["base_url"]
# )
# history = [{
#     "role": "system",
#     "content": '''
# 你是一个智能助手，拥有调用工具的能力，可以帮助用户解决遇到的问题。

# 当你需要调用工具时，你需要**只以 JSON 格式输出一个数组**，数组中的每个元素是一个字典，取值为以下两种：
# 1. `{"name": "python", "code": ""}` 表示调用 Python 执行代码，`code` 为 Python 代码字符串。
# 2. `{"name": "bash", "code": ""}` 表示调用 Bash 执行代码，`code` 为 Bash 代码字符串。
# 如果执行成功，你将会在下一次输入时得到调用代码的 stdout 结果，否则，你将收到 stderr 的结果。

# 比如：
# 用户提问：请介绍一下我的 Python 版本。
# 你的输出：
# ```json
# [{"name": "bash", "code": "python3 --version"}]
# ```
# 用户返回：[{"name": "bash", "code": "python3 --version", "stdout": "Python 3.12.7\n"}]

# 然后，你可以正常回答用户的问题。
# 注意，只有在你以 ```json ... ``` 格式输出时，才会调用工具。否则，你并不会收到调用工具的结果。
# 所以，当你希望调用工具时，**请不要有任何其他的输出和提示**。

# 你需要合理思考，灵活运用工具，帮助用户解决遇到的问题！
# '''
# }]



# def chat(content, model):
#     global history
#     history.append({
#         "role": "user",
#         "content": content
#     })
#     # print('content', content)
#     # return input_lines('>> MODEL >>'), ''
#     # '''
#     # ```json \
#     # [{"name": "bash", "code": "uname -a"}, {"name": "python", "code": "print(\"Hello, World!\")"}] \
#     # [{"name": "bash", "code": "uname -a"}]
#     # ```
#     # '''
#     response = client.chat.completions.create(
#         model=model,
#         messages=history,
#         stream=True
#     )
#     reasoning, answering = "", ""
#     is_reasoning, is_answering = False, False
#     for chunk in response:
#         if not chunk.choices:
#             continue
#         delta = chunk.choices[0].delta
#         if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
#             if not is_reasoning:
#                 print(">> Reasoning >>")
#                 is_reasoning = True
#             print(delta.reasoning_content, end="", flush=True)
#             reasoning += delta.reasoning_content
#         else:
#             if not is_answering:
#                 print(">> Answering >>")
#                 is_answering = True
#             print(delta.content, end="", flush=True)
#             answering += delta.content
#     if is_reasoning or is_answering:
#         print()
#     history.append({
#         "role": "assistant",
#         "content": answering
#     })
#     return answering, reasoning

# def main():
#     global history, config
#     model = config["model"]
#     while True:
#         content = input(">> ")
#         if content == "exit":
#             break

#         for _ in range(20):
#             answering, reasoning = chat(content, model)
#             cmd = None
#             answering = re.search(r'^(.*?)```(.*?)\n(.*)\n```(.*?)$', 
#                                   answering.strip(), re.S).groups()
#             if len(answering) == 4 and answering[1] == 'json':
#                 try:
#                     print('Parsing', answering[2])
#                     cmd = json.loads(answering[2])
#                     if type(cmd) is not list:
#                         raise Exception("Invalid type")
#                     for c in cmd:
#                         if type(c) is not dict:
#                             raise Exception("Invalid type")
#                         if "name" not in c:
#                             raise Exception("Invalid format")
#                         res = None
#                         if c['name'] == 'python':
#                             if 'code' not in c:
#                                 raise Exception("Invalid Python call format")
#                             ret = subprocess.run(['python3', '-c', c['code']], capture_output=True)
#                             if ret.returncode == 0:
#                                 res = { "stdout": ret.stdout.decode('utf-8') }
#                             else:
#                                 res = { "stderr": ret.stderr.decode('utf-8') }
#                         elif c['name'] == 'bash':
#                             if 'code' not in c:
#                                 raise Exception("Invalid bash call format")
#                             ret = subprocess.run(c['code'], shell=True, capture_output=True)
#                             if ret.returncode == 0:
#                                 res = { "stdout": ret.stdout.decode('utf-8') }
#                             else:
#                                 res = { "stderr": ret.stderr.decode('utf-8') }
#                         c.update(res)
#                     content = json.dumps(cmd, ensure_ascii=False)
                    
#                     print('>> RUN >>')
#                     for c in cmd:
#                         print(f'[{c["name"]}] {c["code"]!r}', end='')
#                         if 'stdout' in c:
#                             print(f' -> stdout')
#                             print(c['stdout'])
#                         if 'stderr' in c:
#                             print(f' -> stderr')
#                             print(c['stderr'])
#                     print('>> RUN FINISHED >>')
#                 except Exception as err:
#                     print('Parsing error:', err)
#                     break
#             if cmd is None: break

# if __name__ == "__main__":
#     main()
#     print(json.dumps(history, ensure_ascii=False))