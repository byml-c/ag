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
with open('template_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
config['root'] = os.path.abspath(os.path.dirname(__file__))
with open('config.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print('安装完成！')