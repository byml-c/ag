import os
import re
import json
import traceback
import subprocess

from chat import Chat
from execute import check_parse, parse_and_exec

class Deep(Chat):
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
            if result.get('reasoning', None) is not None:
                history['history'][-1].update({"reasoning": result['reasoning']})

            commands = check_parse(result['answer'])
            if commands is None:
                print('╰─────────────')
                return 'finish', '', history
            else:
                # 解析出可执行代码
                print('├─ RUN')
                outputs, content = parse_and_exec(commands)
                print(outputs, end='')
                print('╰─────────────')
                return 'exec', content, history
        except KeyboardInterrupt:
            print()
            print("╭─    中断")
            print("╰─  本轮对话已停止。")
            return 'finish', '', history