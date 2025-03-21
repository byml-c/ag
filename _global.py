import sys
from pathlib import Path

# 配置文件路径
ROOT_DIR = Path("/home/byml/projects/my-style/ai_agent")
THIRDPARTY   = ROOT_DIR / "thirdparty"
CONFIG_FILE  = ROOT_DIR / "config"  / "config.json"
DATA_DIR     = ROOT_DIR / ".agdata"
VARS_FILE    = DATA_DIR / "vars.json"
HISTORY_DIR  = DATA_DIR / "history"
HISTORY_FILE = DATA_DIR / "history.json"
SNIPPETS_DIR = DATA_DIR / "snippets"

# 历史记录文件格式
HISTORY_FORMAT = r"%Y-%m-%d_%H-%M-%S"

# 将 thirdparty 加入 sys.path
sys.path.insert(0, str(THIRDPARTY.absolute()))