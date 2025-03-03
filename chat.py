import os
import re
import traceback
from openai import OpenAI
from render import MDStreamRenderer

class Chat:
    def __init__(self, api_key:str, base_url:str):    
        os.environ['all_proxy'] = ''
        os.environ['http_proxy'] = ''
        os.environ['https_proxy'] = ''
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
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
    
    def _render_history(self, history:dict[str, list]):
        '''
            打印历史记录，同时会清空 history['snippet'] 并重新生成
        '''
        class Delta:
            def __init__(self, c, r):
                if r:
                    self.reasoning_content = c
                else:
                    self.content = c
        class Choice:
            def __init__(self, c, r):
                self.delta = Delta(c, r)
        class Chunk:
            def __init__(self, text, reasoning=False):
                self.choices = [
                    Choice(text, reasoning)
                ]
        def gen(s:str, batch:int=100):
            for i in range(0, len(s), batch):
                yield Chunk(s[i:i+batch])

        history['snippet'] = []
        for item in history['history']:
            if item['role'] == 'user':
                print(f"╭─  󱋊  User")
                print(f"╰─  {item['content']}")
            elif item['role'] == 'assistant':
                print(f"╭─  󱚣  Model")
                try:
                    hist, _ = self._render_response(gen(item['content']))
                    history['snippet'] += hist['snippet']
                except:
                    print(traceback.format_exc())
                print(f'╰─────────────')
        return history
    
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
            _, answer_content = self._render_response(response, history)
            print('╰─────────────')
            history['history'].append({
                "role": "assistant",
                "content": answer_content
            })
        except KeyboardInterrupt:
            print()
            print("╭─    中断")
            print("╰─  本轮对话已停止。")
        finally:
            return 'finish', history