Write-Host "Setting up the working directory"
$ROOT_DIR = Get-Location
$ROOT_DIR_R = $ROOT_DIR -replace '[\, /, \\]', '\\'
$ROOT_DIR_REX = "(ROOT_DIR = Path\().*(\))", "`$1r`"$ROOT_DIR_R`"`$2"
(Get-Content ag.py) -replace $ROOT_DIR_REX | Set-Content ag.py

if (Test-Path -Path "config.json") {
    Write-Host "`config.json` already exists!"
} else {
    Write-Host "Creating config.json"
    @'
{
    "api_key": "",
    "base_url": "",
    "system_prompt": "You are an assistant. Answer briefly, professionally. Very important: Answer in Chinese.",
    "chat_prompt": "你是一个熟悉计算机并具有丰富教学经验的 AI 助手，无论提出问题的是什么语言，请用中文简明扼要地回答我的问题。",
    "deep_prompt": "\n你是一个智能助手，拥有调用工具的能力，可以帮助用户解决遇到的问题。\n\n当你需要调用工具时，你需要**只以 JSON 格式输出一个数组**，数组中的每个元素是一个字典，取值为以下两种：\n1. `{\"name\": \"python\", \"code\": \"\"}` 表示调用 Python 执行代码，`code` 为 Python 代码字符串。\n2. `{\"name\": \"bash\", \"code\": \"\"}` 表示调用 Bash 执行代码，`code` 为 Bash 代码字符串。\n如果执行成功，你将会在下一次输入时得到调用代码的 stdout 结果，否则，你将收到 stderr 的结果。\n\n比如：\n用户提问：请介绍一下我的 Python 版本。\n你的输出：\n```json\n[{\"name\": \"bash\", \"code\": \"python3 --version\"}]\n```\n用户返回：[{\"name\": \"bash\", \"code\": \"python3 --version\", \"stdout\": \"Python 3.12.7\n\"}]\n\n然后，你可以正常回答用户的问题。\n注意，只有在你以 ```json ... ``` 格式输出时，才会调用工具。否则，你并不会收到调用工具的结果。\n所以，当你希望调用工具时，**请不要有任何其他的输出和提示**。\n\n你需要合理思考，灵活运用工具，帮助用户解决遇到的问题！\n",
    "models": [
        {
            "model": "",
            "alias": [""]
        }
    ],
    "model": "",
    "deep": false, 
}
'@ | Out-File -FilePath "config.json" -Encoding utf8
}

Write-Host "--------------------"
while ($true) {
    $answer = Read-Host "Do you want to add alias ag to profile.ps1? (y/n)"
    $answer = $answer.ToLower()

    if ($answer -eq "y") {
        $aliasCommand = "Set-Alias -Name ag -Value `"$($ROOT_DIR)\\ag.py`""
        Add-Content -Path $PROFILE -Value $aliasCommand
        . $PROFILE
        break
    } elseif ($answer -eq "n") {
        Write-Host "Skipping..."
        break
    } else {
        Write-Host "Invalid input, please enter y or n."
    }
}

Write-Host "--------------------"
Write-Host "`e[32m`e[1mInstallation complete!`e[0m"
Write-Host "`e[34m`e[1mPlease fill in the `config.json` file with your API key and base URL.`e[0m"
Write-Host "You can run the program by:"
Write-Host "    1. python ag.py"
Write-Host "    2. Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser and then ./ag.py"