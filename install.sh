#!/bin/bash
echo "Setting up the working directory"
ROOT_DIR=$(pwd)
ROOT_DIR_R=$(echo $ROOT_DIR | sed -E 's/\//\\\//g')
ROOT_DIR_REX='1,$s/(ROOT_DIR\s=\sPath\(\").*?(\"\))/\1'$ROOT_DIR_R'\2/'
sed -i -E $ROOT_DIR_REX ai.py

if [[ -f config.json ]]; then
    echo "\`config.json\` already exists!"
else
    echo "Creating config.json"
    echo '{
    "api_key": "",
    "base_url": "",
    "system_prompt": "你是一个熟悉计算机并具有丰富教学经验的 AI 助手，无论提出问题的是什么语言，请用中文简明扼要地回答我的问题。","chat_prompt": "你是一个熟悉计算机并具有丰富教学经验的 AI 助手，无论提出问题的是什么语言，请用中文简明扼要地回答我的问题。",
    "deep_prompt": "你是一个智能助手，拥有调用工具的能力，可以帮助用户解决遇到的问题。\n\n当你需要调用工具时，你需要**只以 JSON 格式输出一个数组**，数组中的每个元素是一个字典，取值为以下两种：\n1. `{\"name\": \"python\", \"code\": \"\"}` 表示调用 Python 执行代码，`code` 为 Python 代码字符串。\n2. `{\"name\": \"bash\", \"code\": \"\"}` 表示调用 Bash 执行代码，`code` 为 Bash 代码字符串。\n如果执行成功，你将会在下一次输入时得到调用代码的 stdout 结果，否则，你将收到 stderr 的结果。\n\n比如：\n用户提问：请介绍一下我的 Python 版本。\n你的输出：\n```json\n[{\"name\": \"bash\", \"code\": \"python3 --version\"}]\n```\n用户返回：[{\"name\": \"bash\", \"code\": \"python3 --version\", \"stdout\": \"Python 3.12.7\n\"}]\n\n然后，你可以正常回答用户的问题。\n注意，只有在你以 ```json ... ``` 格式输出时，才会调用工具。否则，你并不会收到调用工具的结果。\n所以，当你希望调用工具时，**请不要有任何其他的输出和提示**。\n\n你需要合理思考，灵活运用工具，根据运行结果灵活调整策略，帮助用户解决遇到的问题！",
    "models": [
        {
            "model": "",
            "alias": [""]
        }
    ],
    "model": "",
    "deep": false
}' > config.json
fi

echo "--------------------"
while true; do
    read -p "Do you want to add alias \`ag\` to .bashrc? (y/n)" answer
    answer=$(echo "$answer" | tr '[:upper:]' '[:lower:]')

    if [ "$answer" = "y" ]; then
        echo "alias ag='"$(which python3) $ROOT_DIR"/ai.py'" >> ~/.bashrc
        source ~/.bashrc
        break
    elif [ "$answer" = "n" ]; then
        echo "Skipping..."
        break
    else
        echo "Invalid input, please enter y or n."
    fi
done

echo "--------------------"
echo -e "\033[32m\033[1mInstallation complete!\033[0m"
echo -e "\033[34m\033[1mPlease fill in the \`config.json\` file with your API key and base URL.\033[0m"
echo -e "You can run the program by:"
echo -e "    1. \`python3 ai.py\`"
echo -e "    2. \`sudo chmod +x ai.py\` and then \`./ai.py\`"
