#!/bin/env python3

import os
import json

try:
    from openai import OpenAI
except ImportError:
    print('正在安装 openai 模块...')
    os.system('pip install openai')

if os.name == 'posix':
    import readline
elif os.name == 'nt':
    try:
        import pyreadline3 as readline
    except ImportError:
        print('正在安装 pyreadline 模块...')
        os.system('pip install pyreadline')

print("正在创建配置文件...")
with open('./package/template_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
with open('config.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

with open('./package/ai.py', 'r', encoding='utf-8') as f:
    ai = f.read().replace(
        'root_path_of_this_file', os.path.dirname(
            os.path.abspath(__file__)).replace('\\', '/'))
with open('ai.py', 'w', encoding='utf-8') as f:
    f.write(ai)

print('正在删除安装文件...')
os.removedirs('./package')
print('安装完成！')