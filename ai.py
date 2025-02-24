#!/home/byml/app/anaconda3/bin/python
import os
import sys
import json
from pathlib import Path
from openai import OpenAI, Transport

# 配置文件路径
CONFIG_DIR = Path("/home/byml/projects/my-style/ai_agent")
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"

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
    
    def save_config(self):
        """保存配置"""
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def find_model(self, s:str):
        for model in self.config["models"]:
            if model["model"] == s:
                return model
            for alias in model["alias"]:
                if alias == s:
                    return model
        return None

    def chat(self):
        """执行对话"""
        try:
            user_name = os.getenv("USER")
            # 交互模式
            while True:
                user_input = input(f"\n╭─  󱋊 {user_name}\n╰─  ").strip()
                
                if user_input.lower() == 'help':
                    print()
                    print("╭─  󰘥  Help")
                    print("│   clear : 清空历史")
                    print("│   change: 切换模型")
                    print("│   help  : 查看帮助")
                    print("│   exit  : 退出")
                    print("╰─────────────")
                    continue
                if user_input[:6].lower() == 'change':
                    if user_input == 'change':
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
                        model = user_input[7:]
                    model = self.find_model(model)
                    if model is not None:
                        self.config["model"] = model
                        self.save_config()
                        print("╰─    模型切换成功")
                    else:
                        print("╰─    模型不存在")
                    continue
                if user_input.lower() == 'clear':
                    self.history = [self.history[0]]
                    print()
                    print("╭─    清空历史")
                    print("╰─  历史已清空。")
                    continue
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    self.save_history()
                    print()
                    print("╭─    再见")
                    print("╰─  历史已保存。")
                    break
                
                self.history.append({"role": "user", "content": user_input})
                
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
                            if is_reasoning:
                                print('\n├─────────────')
                            print("├─  󰛩  ANSWER \n│   ", end="",flush=True)
                            is_answering = True
                        # 打印回复过程
                        print(delta.content.replace('\n', '\n│   '), end="", flush=True)
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
            print("╰─  历史已保存。")
        except Exception as e:
            print()
            print(f"╭─    错误")
            print(f"╰─  {str(e)}")
            self.save_history()

def main():
    ai = AIChat()
    ai.chat()

if __name__ == "__main__":
    main()
