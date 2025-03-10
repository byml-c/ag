import time
import random
from _global import *

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

tt = [
    "以下是将你的 Bash 脚本转换为 PowerShell 脚本的版本：\n\n```powershell\n# 检查是否安装了 Python3\nif (-not (Get-Command python3 -ErrorAction SilentlyContinue)) {\n    Write-Host \"Installing Python3\"\n    sudo apt-get install python3\n}\n\n# 检查是否安装了 pip3\nif (-not (Get-Command pip3 -ErrorAction SilentlyContinue)) {\n    Write-Host \"Installing pip3\"\n    sudo apt-get install python3-pip\n}\n\n# 检查是否安装了 openai 包\nif (-not (pip show openai -ErrorAction SilentlyContinue)) {\n    Write-Host \"Installing openai\"\n    pip3 install openai\n}\n\nWrite-Host \"--------------------\"\nWrite-Host \"Setting up the working directory\"\n$ROOT_DIR = Get-Location\n$ROOT_DIR_R = $ROOT_DIR.Path.Replace(\"\\\", \"\\\\\")\n$ROOT_DIR_REX = '1,$s/(ROOT_DIR\\s=\\sPath\\(\\\").*?(\\\"\\))/\\1' + $ROOT_DIR_R + '\\2/'\n(Get-Content ai.py) -replace 'ROOT_DIR\\s=\\sPath\\(\\\".*?\\\"\\)', \"ROOT_DIR = Path(`\"$ROOT_DIR`\")\" | Set-Content ai.py\n\n# 检查是否存在 config.json 文件\nif (Test-Path config.json) {\n    Write-Host \"`config.json` already exists!\"\n} else {\n    Write-Host \"Creating config.json\"\n    @'\n{\n    \"api_key\": \"\",\n    \"base_url\": \"\",\n    \"system_prompt\": \"你是一个熟悉计算机并具有丰富教学经验的 AI 助手，无论提出问题的是什么语言，请用中文回答我的问题\",\n    \"models\": [\n        {\n            \"model\": \"deepseek-v3\",\n            \"alias\": [\"v3\"]\n        },\n        {\n            \"model\": \"deepseek-r1\",\n            \"alias\": [\"r1\"]\n        }\n    ],\n    \"model\": \"deepseek-v3\",\n    \"temperature\": 0.5,\n    \"max_history\": 100\n}\n'@ | Set-Content config.json\n}\n\nWrite-Host \"--------------------\"\nwhile ($true) {\n    $answer = Read-Host \"Do you want to add alias `ag` to your PowerShell profile? (y/n)\"\n    $answer = $answer.ToLower()\n\n    if ($answer -eq \"y\") {\n        $pythonPath = (Get-Command python3).Source\n        $aliasCommand = \"function ag { & '$pythonPath' '$ROOT_DIR\\ai.py' @args }\"\n        Add-Content -Path $PROFILE -Value $aliasCommand\n        . $PROFILE\n        break\n    } elseif ($answer -eq \"n\") {\n        Write-Host \"Skipping...\"\n        break\n    } else {\n        Write-Host \"Invalid input, please enter y or n.\"\n    }\n}\n\nWrite-Host \"--------------------\"\nWrite-Host -ForegroundColor Green -BackgroundColor Black \"Installation complete!\"\nWrite-Host -ForegroundColor Blue -BackgroundColor Black \"Please fill in the `config.json` file with your API key and base URL.\"\nWrite-Host \"You can run the program by:\"\nWrite-Host \"    1. `python3 ai.py`\"\nWrite-Host \"    2. `chmod +x ai.py` and then `.\\ai.py`\"\n```\n\n### 主要更改点：\n1. **命令替换**：\n   - `which` 替换为 `Get-Command`。\n   - `sed` 替换为 PowerShell 的字符串替换操作。\n   - `echo` 替换为 `Write-Host`。\n   - `read` 替换为 `Read-Host`。\n\n2. **路径处理**：\n   - `pwd` 替换为 `Get-Location`。\n   - 路径分隔符 `\\` 在 PowerShell 中需要转义为 `\\\\`。\n\n3. **别名添加**：\n   - 在 PowerShell 中，别名通过 `function` 定义，并添加到 `$PROFILE` 文件中。\n\n4. **颜色输出**：\n   - 使用 `Write-Host` 的 `-ForegroundColor` 和 `-BackgroundColor` 参数来实现颜色输出。\n\n### 注意事项：\n- 该脚本假设你在 Windows 上使用 PowerShell，并且已经安装了 Python3 和 pip3。\n- 如果你在 Linux 或 macOS 上使用 PowerShell Core，可能需要调整部分命令（如 `sudo apt-get`）。",
    
    "```python\nprint('abc')\n```\n另一端代码\n```js\nconsole.log(\"def\")\n```\n再看看 bash\n```bash\necho xxx\n```\n",
    
    "看起来你的系统中没有安装 `lsblk` 工具。`lsblk` 通常预装在 Linux 系统中，但如果你使用的是 Windows 系统，默认是没有这个工具的。\n\n### 解决方案\n1. **如果你使用的是 Linux 系统**：\n   - 确保 `lsblk` 已安装。你可以通过以下命令安装它：\n     ```bash\n     sudo apt-get install util-linux\n     ```\n   - 安装后，再次运行 `lsblk`。\n\n2. **如果你使用的是 Windows 系统**：\n   - `lsblk` 是 Linux 工具，Windows 上没有直接等效的工具。你可以使用以下替代方法：\n     - 使用 `diskpart` 命令查看磁盘信息：\n       ```bash\n       diskpart\n       list disk\n       ```\n     - 或者使用 PowerShell 命令：\n       ```powershell\n       Get-Disk\n       ```\n\n### 示例（Linux）\n假设你已安装 `lsblk`，以下是一个示例输出：\n```bash\nNAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT\nsda      8:0    0   100G  0 disk \n├─sda1   8:1    0    50G  0 part /\n└─sda2   8:2    0    50G  0 part /home\n```\n\n如果你需要进一步帮助，请告诉我你的操作系统环境！",
    
    "`lsblk` 是一个用于列出块设备信息的命令行工具。它显示系统中所有块设备（如硬盘、分区、挂载点等）的树状结构，帮助用户快速了解存储设备的布局。\n\n### 基本用法\n```bash\nlsblk\n```\n\n### 常用选项\n- `-a`：显示所有设备，包括空设备。\n- `-f`：显示文件系统类型。\n- `-o`：指定输出的列（如 NAME, SIZE, FSTYPE, MOUNTPOINT 等）。\n- `-p`：显示完整设备路径（如 `/dev/sda1`）。\n\n### 示例\n1. **列出所有块设备**：\n   ```bash\n   lsblk\n   ```\n\n   输出示例：\n   ```\n   NAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT\n   sda      8:0    0   100G  0 disk \n   ├─sda1   8:1    0    50G  0 part /\n   └─sda2   8:2    0    50G  0 part /home\n   ```\n\n2. **显示文件系统类型**：\n   ```bash\n   lsblk -f\n   ```\n   输出示例：\n   ```\n   NAME   FSTYPE LABEL UUID                                 MOUNTPOINT\n   sda                                                       \n   ├─sda1 ext4   root  c1b9d5a2-3e7f-4b1e-8e3a-9c8b7d6e5f4a /\n   └─sda2 ext4   home  d2e8f9a1-4b6c-4d7e-8f2a-1b3c4d5e6f7b /home\n   ```\n\n3. **自定义输出列**：\n   ```bash\n   lsblk -o NAME,SIZE,MOUNTPOINT\n   ```\n   输出示例：\n   ```\n   NAME   SIZE MOUNTPOINT\n   sda    100G \n   ├─sda1  50G /\n   └─sda2  50G /home\n   ```\n\n`lsblk` 是一个简单但功能强大的工具，适合快速查看系统存储设备的状态。",
    
    "### 示例\n1. **列出所有块设备**：\n   ```bash\n   lsblk\n   ```\n   输出示例：\n   ```\n   NAME   MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT\n   sda      8:0    0   100G  0 disk \n   ├─sda1   8:1    0    50G  0 part /\n   └─sda2   8:2 0    50G  0 part /home\n   ```\n\n"]

def gen():
    global tt
    ct = str(tt[1])
    while len(ct) > 0:
        time.sleep(0.05*random.random())
        l = random.randint(8, 18)
        if l > len(ct):
            yield Chunk(ct)
            break
        else:
            nt, ct = ct[:l], ct[l:]
            yield Chunk(nt)

def parse():
    import re
    import json
    import traceback
    
    s = '\n\n```json\n[{\"name\": \"bash\", \"code\": \"git status --porcelain\"}, {\"name\": \"bash\", \"code\": \"git diff HEAD\"}]\n```'
    commands = []
    s = re.search(r'^([\s\S]*?)```(.*?)\n([\s\S]*)\n```([\s\S]*?)$', 
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
            traceback.print_exc()
    print(commands)
    return commands if len(commands) > 0 else None

def main():
    import rich
    from rich.markdown import Markdown
    from rich.console import Console

    with open('Readme.md', 'r', encoding='utf-8') as f:
        tt[4] = f.read()
    console = Console()
    md = Markdown(tt[4])
    console.print(md)
    # print(md.parsed)
    # rich.inspect(console=console, obj=md.parsed)

if __name__ == '__main__':
    main()
    # parse()
    