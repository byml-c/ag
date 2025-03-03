Write-Host "Setting up the working directory"
$ROOT_DIR = Get-Location
$ROOT_DIR_R = $ROOT_DIR -replace '[\, /]', '\\'
$ROOT_DIR_REX = "(ROOT_DIR = Path\(`")PATH_TO_AG(`"\))", "`$1$ROOT_DIR_R`$2"
(Get-Content ai.py) -replace $ROOT_DIR_REX | Set-Content ai.py

if (Test-Path -Path "config.json") {
    Write-Host "`config.json` already exists!"
} else {
    Write-Host "Creating config.json"
    @'
{
    "api_key": "",
    "base_url": "",
    "system_prompt": "你是一个熟悉计算机并具有丰富教学经验的 AI 助手，无论提出问题的是什么语言，请用中文回答我的问题",
    "models": [
        {
            "model": "",
            "alias": [""]
        }
    ],
    "model": "",
    "temperature": 0.5
}
'@ | Out-File -FilePath "config.json" -Encoding utf8
}

Write-Host "--------------------"
while ($true) {
    $answer = Read-Host "Do you want to add alias ag to profile.ps1? (y/n)"
    $answer = $answer.ToLower()

    if ($answer -eq "y") {
        $aliasCommand = "Set-Alias -Name ag -Value `"$($ROOT_DIR)\\ai.py`""
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
Write-Host "    1. python ai.py"
Write-Host "    2. Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser and then ./ai.py"