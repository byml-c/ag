import time
import random

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
    "```python\nprint('abc')\n```\n另一端代码\n```js\nconsole.log(\"def\")\n```\n再看看 bash\n```bash\necho xxx\n```\n"]

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

def main():
    pass

if __name__ == '__main__':
    main()