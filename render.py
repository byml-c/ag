import os
import re
import sys

sys.path.insert(0, "./thirdparty")

from thirdparty.rich.markdown import Markdown
from thirdparty.rich.console import Console
from thirdparty.rich.style import Style
from thirdparty.rich.theme import Theme
from thirdparty.rich.text import Text
from thirdparty.rich.live import Live

# 自定义主题
custom_theme = Theme(
    {
        "markdown.block_quote": "#999999 on #1f1f1f",
        "markdown.block_quote_border": "#d75f00",
        "markdown.h1": "bold #1E90FF",
        "markdown.h2": "bold #00BFFF",
        "markdown.h3": "bold #87CEFA",
        "markdown.h4": "bold #87CEEB",
        "markdown.h5": "bold #E0FFFF",
        "markdown.h6": "#E0FFFF",
        "live.ellipsis": "#e6db74 on #272822",
    }
)
console = Console(theme=custom_theme)


class MDStreamRenderer:
    def __init__(self, code_start: int):
        self.md = None
        self.live = None
        self.code_start = code_start
        self.code_list = []
        self.buffer = ""

    def __enter__(self):
        self._new()
        self.code_list = []
        return self

    def _new(self, text=""):
        if self.md is not None:
            self.live.__exit__(None, None, None)
        self.buffer = text
        self.live = Live(console=console, refresh_per_second=10)
        self.live.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.live is None:
            return
        self.live.__exit__(exc_type, exc_value, traceback)

    def _add_snippet(self, lang, code):
        self.code_list.append({"lang": lang, "code": code})
        sid = self.code_start + len(self.code_list) - 1
        console.print(
            Text(f"   snippet {sid}  ", justify="left", style="#e6db74 on #272822"),
            Text(f"", justify="left", style="#272822"),
            sep="",
        )

    def _update(self, edl: str = "", reasoning: bool = False):
        def _new_md(buffer: str):
            return Markdown(buffer, code_theme="monokai", inline_code_lexer="text")

        self.buffer += edl
        try:
            last_pose = self.buffer.rfind("```")
            if last_pose == -1:
                self.md = _new_md(self.buffer)
                self.live.update(self.md, refresh=True)
                if edl == "\n\n" or (edl == "\n" and reasoning):
                    self._new()
            else:
                if self.buffer[:3] == "```":
                    self.md = _new_md(self.buffer)
                    code = self.md.parsed[-1]
                    self.live.update(self.md, refresh=True)
                    if last_pose != 0:
                        self._add_snippet(code.info, code.content)
                        self._new(self.buffer[last_pose + 3 :])
                else:
                    self.md = _new_md(self.buffer[:last_pose])
                    self.live.update(self.md, refresh=True)
                    self._new(self.buffer[last_pose:])
        except:
            self.live.update(Text(self.buffer), refresh=True)

    def update(self, chunk: str, reasoning: bool = False):
        chunk = re.sub(r"\n{2,}", "\n\n", chunk)
        length, i, newline = len(chunk), 0, False
        while i < length:
            if chunk[i] == "\n":
                newline = False
                if i + 1 < length and chunk[i + 1] == "\n":
                    self._update("\n\n")
                    i = i + 1
                else:
                    self._update("\n", reasoning)
            else:
                newline = True
                self.buffer += chunk[i]
            i += 1
        if newline:
            self._update()
