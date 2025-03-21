import re
import os
import io
import sys
import json
import time
import base64
import traceback
import subprocess
import numpy as np
from PIL import Image
from pathlib import Path
from openai import OpenAI
from _global import *

def bash(cmd):
    '''
        使用 bash 命令执行
    '''
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, text=True, stdin=sys.stdin, capture_output=True)
        cost_time = int((time.time() - start_time) * 1000)
        return result.stdout.strip(), result.stderr.strip(), cost_time, result.returncode
    except subprocess.CalledProcessError as e:
        cost_time = int((time.time() - start_time) * 1000)
        return e.stdout.strip(), e.stderr.strip(), cost_time, e.returncode
    except Exception as e:
        cost_time = int((time.time() - start_time) * 1000)
        return "\033[91m---   Unexcepted Error! ---\033[0m", traceback.format_exc(), cost_time, -1

def check_parse(s:str):
    '''
        检查并解析命令
    '''
    commands = []
    s = re.search(r'^(\s*?)```json\n(.*)\n```(\s*?)$', 
                    s.strip(), re.S)
    if s is None:
        return None
    s = s.groups()
    
    if len(s) == 3:
        try:
            cmd = json.loads(s[1])
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

def parse_and_exec(commands:list[dict]):
    '''
        解析并执行命令
    '''
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
    
    outputs = '''''' 
    for cmd in commands:
        outputs += f'[{cmd["name"]}] {cmd["code"]!r}'
        if 'stdout' in cmd:
            outputs += f' -> stdout[ExitCode: 0]\n'
            outputs += cmd['stdout']+'\n'
        if 'stderr' in cmd:
            outputs += f' -> stderr[ExitCode: {cmd["exitcode"]}]\n'
            outputs += cmd['stderr']+'\n'
    return outputs, json.dumps(commands, ensure_ascii=False)

def parse_para(para:str):
    '''
        解析参数
    '''
    return [i.strip() for i in para.split(',')]

# 自定义函数，传入参数应均为字符串列表
func_description = [
    {
        'name': 'file',
        'icon': ' ',
        'para': [('str', 'file path')],
        'des': '使用 cat 方法获取文件内容，返回文件内容。'
    },
    {
        'name': 'screen',
        'icon': ' ',
        'para': [('str[option]', 'info')],
        'des': '获取屏幕截图，并交由本地 VLM 解释，返回描述。可以通过 info 添加额外描述，以帮助 VLM 更好地解释图片。'
    },
    {
        'name': 'image',
        'icon': ' ',
        'para': [('str', 'file path'), ('str[option]', 'info')],
        'des': '将图片交由本地 VLM 解释，返回描述。可以通过 info 添加额外描述，以帮助 VLM 更好地解释图片。'
    }
]
def file(args:list[str]) -> str:
    if len(args) < 0:
        raise IndexError('parameter is empty!')
    
    path = args[0]
    if not Path(path).exists():
        raise FileNotFoundError(f"file {path} not exists!")
    
    out, err, _, exitcode = bash(f'cat {path}')
    if exitcode == 0:
        return out
    else:
        raise RuntimeError(f"fail to fetch {path}, stderr: "+err)

def image(args:list[str]) -> str:
    if len(args) < 1:
        raise IndexError('parameter is empty!')
    image_path = args[0]
    if not Path(image_path).exists():
        raise FileNotFoundError(f"file {image_path} not exists!")
    
    if len(args) > 1:
        info = ''.join(args[1:])
    else: info = None
    
    try:
        with open(image_path, 'rb') as img:
            img_data_url = f"data:image/png;base64,{base64.b64encode(img.read()).decode()}"
        
        os.environ['all_proxy'] = ''
        os.environ['http_proxy'] = ''
        os.environ['https_proxy'] = ''
        client = OpenAI(
            api_key="Ollama",
            base_url="http://localhost:11434/v1/"
        )
        start = time.time()
        response = client.chat.completions.create(
            model="minicpm-v:latest",
            messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "你会收到一张屏幕截图，你需要尽量详细地描述屏幕中的内容。" if info is None \
                                else "你会收到一张屏幕截图，请从截图中提取信息，回答这个问题：屏幕中，"+info
                        },
                        {
                            "type": "image_url",
                            "image_url": img_data_url,
                        }
                    ]
                }],
            temperature=0.7,
            stream=True
        )
        res = ''
        for chunk in response:
            content = chunk.choices[0].delta.content
            res += content
            print(f'\r  {" "*100}', end='')
            print(f'\r {res[-50:].replace("\n", " ")}', end='', flush=True)
        print(f'\r  {" "*100}', end='')
        print(f'\r生成完成，共 {len(res)} 字，耗时 {time.time()-start:.2f} 秒。', flush=True)
        return res
    except:
        print('生成出错：', traceback.format_exc())
        raise Exception('生成出错')

def screen(args:list[str]) -> str:
    print('倒计时：', end='')
    for i in range(3, 0, -1):
        print(i, end=' >> ', flush=True)
        time.sleep(1)
    
    img_path = DATA_DIR / "tmp.png"
    bash(f'gnome-screenshot -f {img_path.__str__()}')
    print('截图完成，VLM 处理中……')
    return image(args=[img_path.__str__(), *args])