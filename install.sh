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
    "system_prompt": "你是一个熟悉计算机并具有丰富教学经验的 AI 助手，无论提出问题的是什么语言，请用中文回答我的问题",
    "models": [
        {
            "model": "",
            "alias": [""]
        }
    ],
    "model": "",
    "temperature": 0.5
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
