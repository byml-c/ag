import os
import re

from thirdparty.rich.markdown import Markdown
from thirdparty.rich.console import Console
from thirdparty.rich.style import Style
from thirdparty.rich.theme import Theme
from thirdparty.rich.text import Text
from thirdparty.rich.live import Live

# 自定义主题
custom_theme = Theme({
    "markdown.block_quote": "#999999 on #1f1f1f",
    "markdown.block_quote_border": "#d75f00",
    "markdown.h1": "bold #1E90FF",
    "markdown.h2": "bold #00BFFF",
    "markdown.h3": "bold #87CEFA",
    "markdown.h4": "bold #87CEEB",
    "markdown.h5": "bold #E0FFFF",
    "markdown.h6": "#E0FFFF",
    "live.ellipsis": "#e6db74 on #272822"
})
console = Console(theme=custom_theme)

class MDStreamRenderer:
    def __init__(self, code_start:int):
        self.md = None
        self.live = None
        self.code_start = code_start
        self.code_list = []
        self.content = ""
    
    def __enter__(self):
        self._new()
        self.code_list = []
        return self
    
    def _new(self, text=''):
        if self.md is not None:
            self.live.__exit__(None, None, None)
        self.content = text
        self.live = Live(console=console, refresh_per_second=10)
        self.live.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.live is None:
            return 
        self.live.__exit__(exc_type, exc_value, traceback)

    def _add_snippet(self, lang, code):
        self.code_list.append({"lang": lang, "code": code})
        cid = self.code_start+len(self.code_list)-1
        console.print(Text(f'   snippet {cid}  ', justify='right', style="#e6db74 on #272822"),
                      Text(f'', justify='right', style="#272822"), sep='')

    def _end(self):
        if self.md is not None and len(self.code_list) > 0:
            c = self.md.parsed[-1]
            if c.type == 'fence' and c.block:
                self._add_snippet(c.info, c.content)

    def _update(self, edl:str=''):
        self.content += edl
        try:
            # 使用自定义主题的 Markdown
            self.md = Markdown(
                self.content, 
                code_theme="monokai",
                inline_code_lexer="text"
            )
            c = self.md.parsed[-1]
            if c.type == 'fence' and c.block:
                if len(self.md.parsed) > 1:
                    self.md.parsed.pop()
                    last_pose = self.content.rfind('```')
                    self.live.update(self.md, refresh=True)
                    self._new(self.content[last_pose:])
                else:
                    self.live.update(self.md, refresh=True)
            elif c.type == 'blockquote_close':
                self.live.update(self.md, refresh=True)
                if edl == '\n':
                    self._new()
            else:
                c = self.md.parsed[0]
                if c.type == 'fence' and c.block:
                    code_end = self.content.rfind('```')
                    if code_end != -1:
                        self._add_snippet(c.info, c.content)
                        self._new(self.content[code_end+3:])
                else:
                    self.live.update(self.md, refresh=True)
                    if edl == '\n\n':
                        self._new()
                        console.print()
        except:
            self.live.update(Text(self.content), refresh=True)

    def update(self, chunk:str):
        chunk = re.sub(r"\n{2,}", "\n\n", chunk)
        length, i = len(chunk), 0
        while i < length:
            if chunk[i] == '\n':
                if i+1 < length and chunk[i+1] == '\n':
                    self._update('\n\n')
                    i = i+1
                else:
                    self._update('\n')
            else:
                self.content += chunk[i]
            i += 1
        if self.content != "":
            self._update()