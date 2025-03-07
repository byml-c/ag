import sys
from pathlib import Path

# 配置文件路径
ROOT_DIR = Path("/home/byml/projects/my-style/ai_agent")
THIRDPARTY   = ROOT_DIR / "thirdparty"
CONFIG_FILE  = ROOT_DIR / "config"  / "config.json"
VARS_FILE    = ROOT_DIR / ".agdata" / "vars.json"
HISTORY_DIR  = ROOT_DIR / ".agdata" / "history"
HISTORY_FILE = ROOT_DIR / ".agdata" / "history.json"
SNIPPETS_DIR = ROOT_DIR / ".agdata" / "snippets"

# 历史记录文件格式
HISTORY_FORMAT = r"%Y-%m-%d_%H-%M-%S"

# 将 thirdparty 加入 sys.path
sys.path.append(str(THIRDPARTY.absolute()))