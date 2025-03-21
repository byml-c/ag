from __future__ import annotations

import re
import sys
from typing import ClassVar, Iterable

from markdown_it import MarkdownIt
from mdit_py_plugins.texmath import texmath_plugin
from markdown_it.token import Token

if sys.version_info >= (3, 8):
    from typing import get_args
else:
    from typing_extensions import get_args  # pragma: no cover

from rich.table import Table

from . import box
from ._loop import loop_first
from ._stack import Stack
from .console import Console, ConsoleOptions, JustifyMethod, RenderResult
from .containers import Renderables
from .jupyter import JupyterMixin
from .panel import Panel
from .rule import Rule
from .segment import Segment
from .style import Style, StyleStack
from .syntax import Syntax
from .text import Text, TextType


class MarkdownElement:
    new_line: ClassVar[bool] = True

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> MarkdownElement:
        """Factory to create markdown element,

        Args:
            markdown (Markdown): The parent Markdown object.
            token (Token): A node from markdown-it.

        Returns:
            MarkdownElement: A new markdown element
        """
        return cls()

    def on_enter(self, context: MarkdownContext) -> None:
        """Called when the node is entered.

        Args:
            context (MarkdownContext): The markdown context.
        """

    def on_text(self, context: MarkdownContext, text: TextType) -> None:
        """Called when text is parsed.

        Args:
            context (MarkdownContext): The markdown context.
        """

    def on_leave(self, context: MarkdownContext) -> None:
        """Called when the parser leaves the element.

        Args:
            context (MarkdownContext): [description]
        """

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        """Called when a child element is closed.

        This method allows a parent element to take over rendering of its children.

        Args:
            context (MarkdownContext): The markdown context.
            child (MarkdownElement): The child markdown element.

        Returns:
            bool: Return True to render the element, or False to not render the element.
        """
        return True

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        return ()


class UnknownElement(MarkdownElement):
    """An unknown element.

    Hopefully there will be no unknown elements, and we will have a MarkdownElement for
    everything in the document.

    """


class TextElement(MarkdownElement):
    """Base class for elements that render text."""

    style_name = "none"

    def on_enter(self, context: MarkdownContext) -> None:
        self.style = context.enter_style(self.style_name)
        self.text = Text(justify="left")

    def on_text(self, context: MarkdownContext, text: TextType) -> None:
        self.text.append(text, context.current_style if isinstance(text, str) else None)

    def on_leave(self, context: MarkdownContext) -> None:
        context.leave_style()


class Paragraph(TextElement):
    """A Paragraph."""

    style_name = "markdown.paragraph"
    justify: JustifyMethod

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> Paragraph:
        return cls(justify=markdown.justify or "left")

    def __init__(self, justify: JustifyMethod) -> None:
        self.justify = justify

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        self.text.justify = self.justify
        yield self.text


class Heading(TextElement):
    """A heading."""

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> Heading:
        return cls(token.tag)

    def on_enter(self, context: MarkdownContext) -> None:
        self.text = Text()
        context.enter_style(self.style_name)

    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.style_name = f"markdown.{tag}"
        super().__init__()

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        text = self.text
        h_type = max(0, min(int(self.tag[1:])-1, 6))
        icon = ['󰲡 ', '󰲣 ', '󰲥 ', '󰲧 ', '󰲩 ', '󰲫 '][h_type]
        text = Text(f"{' '*h_type}{icon} ", style=self.style_name).append(text)
        text.justify = 'left'
        yield text


class CodeBlock(TextElement):
    """A code block with syntax highlighting."""

    style_name = "markdown.code_block"

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> CodeBlock:
        node_info = token.info or ""
        lexer_name = node_info.partition(" ")[0]
        return cls(lexer_name or "text", markdown.code_theme, token.meta.get("sid"))

    def __init__(self, lexer_name: str, theme: str, sid:int=None) -> None:
        self.lexer_name = lexer_name
        self.theme = theme
        self.sid = sid

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        code = str(self.text).rstrip()
        syntax = Syntax(
            code, self.lexer_name, theme=self.theme, word_wrap=True,
            line_numbers=True, indent_guides=True
        )
        if self.sid is not None:
            yield Text(f'   snippet {self.sid}  ', style="#e6db74 on #272822", end="")
            yield Text(f'', justify='left', style="#272822")
        yield syntax
        yield Segment("\n")


class BlockQuote(TextElement):
    """A block quote."""

    style_name = "markdown.block_quote"

    def __init__(self) -> None:
        self.elements: Renderables = Renderables()

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        self.elements.append(child)
        return False

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        render_options = options.update(width=options.max_width - 4)
        lines = console.render_lines(self.elements, render_options, style=self.style)
        style = self.style
        new_line = Segment("\n")
        padding = Segment("▌ ", style)
        for line in lines:
            yield padding
            yield from line
            yield new_line


class HorizontalRule(MarkdownElement):
    """A horizontal rule to divide sections."""

    new_line = False

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        style = console.get_style("markdown.hr", default="none")
        yield Rule(style=style)


class TableElement(MarkdownElement):
    """MarkdownElement corresponding to `table_open`."""

    def __init__(self) -> None:
        self.header: TableHeaderElement | None = None
        self.body: TableBodyElement | None = None

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        if isinstance(child, TableHeaderElement):
            self.header = child
        elif isinstance(child, TableBodyElement):
            self.body = child
        else:
            raise RuntimeError("Couldn't process markdown table.")
        return False

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        table = Table(box=box.SIMPLE_HEAVY)
        if self.header is not None and self.header.row is not None:
            for column in self.header.row.cells:
                table.add_column(column.content)
        
        if self.body is not None:
            for row in self.body.rows:
                row_content = [element.content for element in row.cells]
                table.add_row(*row_content)
        yield table


class TableHeaderElement(MarkdownElement):
    """MarkdownElement corresponding to `thead_open` and `thead_close`."""

    def __init__(self) -> None:
        self.row: TableRowElement | None = None

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        assert isinstance(child, TableRowElement)
        self.row = child
        return False


class TableBodyElement(MarkdownElement):
    """MarkdownElement corresponding to `tbody_open` and `tbody_close`."""

    def __init__(self) -> None:
        self.rows: list[TableRowElement] = []

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        assert isinstance(child, TableRowElement)
        self.rows.append(child)
        return False


class TableRowElement(MarkdownElement):
    """MarkdownElement corresponding to `tr_open` and `tr_close`."""

    def __init__(self) -> None:
        self.cells: list[TableDataElement] = []

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        assert isinstance(child, TableDataElement)
        self.cells.append(child)
        return False


class TableDataElement(MarkdownElement):
    """MarkdownElement corresponding to `td_open` and `td_close`
    and `th_open` and `th_close`."""

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> MarkdownElement:
        style = str(token.attrs.get("style")) or ""

        justify: JustifyMethod
        if "text-align:right" in style:
            justify = "right"
        elif "text-align:center" in style:
            justify = "center"
        elif "text-align:left" in style:
            justify = "left"
        else:
            justify = "default"

        assert justify in get_args(JustifyMethod)
        return cls(justify=justify)

    def __init__(self, justify: JustifyMethod) -> None:
        self.content: Text = Text("", justify=justify)
        self.justify = justify

    def on_text(self, context: MarkdownContext, text: TextType) -> None:
        text = Text(text) if isinstance(text, str) else text
        text.stylize(context.current_style)
        self.content.append_text(text)


class ListElement(MarkdownElement):
    """A list element."""

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> ListElement:
        return cls(token.type, int(token.attrs.get("start", 1)), token.level)

    def __init__(self, list_type: str, list_start: int | None, level:int=0) -> None:
        self.items: list[ListItem] = []
        self.list_type = list_type
        self.list_start = list_start
        self.level = level

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        assert isinstance(child, ListItem)
        self.items.append(child)
        return False

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        if self.list_type == "bullet_list_open":
            for item in self.items:
                yield from item.render_bullet(console, options, self.level)
        else:
            number = 1 if self.list_start is None else self.list_start
            last_number = number + len(self.items)
            for index, item in enumerate(self.items):
                yield from item.render_number(
                    console, options, number + index, last_number
                )


class ListItem(TextElement):
    """An item in a list."""

    style_name = "markdown.item"

    def __init__(self) -> None:
        self.elements: Renderables = Renderables()

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        self.elements.append(child)
        return False

    def render_bullet(self, console: Console, options: ConsoleOptions, level:int=0) -> RenderResult:
        render_options = options.update(width=options.max_width - 3)
        lines = console.render_lines(self.elements, render_options, style=self.style)
        bullet_style = console.get_style("markdown.item.bullet", default="none")

        bullet = [' ', ' ', ' ', ' '][(level//2) % 4]
        bullet = Segment(f" {bullet} ", bullet_style)
        padding = Segment(" " * 3, bullet_style)
        new_line = Segment("\n")
        for first, line in loop_first(lines):
            yield bullet if first else padding
            yield from line
            yield new_line

    def render_number(
        self, console: Console, options: ConsoleOptions, number: int, last_number: int
    ) -> RenderResult:
        number_width = len(str(last_number)) + 2
        render_options = options.update(width=options.max_width - number_width)
        lines = console.render_lines(self.elements, render_options, style=self.style)
        number_style = console.get_style("markdown.item.number", default="none")

        new_line = Segment("\n")
        padding = Segment(" " * number_width, number_style)
        numeral = Segment(f"{number}".rjust(number_width - 1) + ". ", number_style)
        for first, line in loop_first(lines):
            yield numeral if first else padding
            yield from line
            yield new_line


class Link(TextElement):
    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> MarkdownElement:
        url = token.attrs.get("href", "#")
        return cls(token.content, str(url))

    def __init__(self, text: str, href: str):
        self.text = Text(text)
        self.href = href


class ImageItem(TextElement):
    """Renders a placeholder for an image."""

    new_line = False

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> MarkdownElement:
        """Factory to create markdown element,

        Args:
            markdown (Markdown): The parent Markdown object.
            token (Any): A token from markdown-it.

        Returns:
            MarkdownElement: A new markdown element
        """
        return cls(str(token.attrs.get("src", "")), markdown.hyperlinks)

    def __init__(self, destination: str, hyperlinks: bool) -> None:
        self.destination = destination
        self.hyperlinks = hyperlinks
        self.link: str | None = None
        super().__init__()

    def on_enter(self, context: MarkdownContext) -> None:
        self.link = context.current_style.link
        self.text = Text(justify="left")
        super().on_enter(context)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        link_style = Style(link=self.link or self.destination or None)
        title = self.text or Text(self.destination.strip("/").rsplit("/", 1)[-1])
        if self.hyperlinks:
            title.stylize(link_style)
        text = Text.assemble("🌆 ", title, " ", end="")
        yield text


greek_map = {
    # greek
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ',
    'epsilon': 'ϵ', 'zeta': 'ζ', 'eta': 'η', 'theta': 'θ',
    'iota': 'ι', 'kappa': 'κ', 'lambda': 'λ', 'mu': 'μ',
    'nu': 'ν', 'xi': 'ξ', 'omicron': 'ο', 'pi': 'π',
    'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ', 'upsilon': 'υ',
    'phi': 'φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω',
    'varphi': 'φ', 'varepsilon': 'ε',
    
    'Alpha': 'Α', 'Beta': 'Β', 'Gamma': 'Γ', 'Delta': 'Δ',
    'Epsilon': 'Ε', 'Zeta': 'Ζ', 'Eta': 'Η', 'Theta': 'Θ',
    'Iota': 'Ι', 'Kappa': 'Κ', 'Lambda': 'Λ', 'Mu': 'Μ',
    'Nu': 'Ν', 'Xi': 'Ξ', 'Omicron': 'Ο', 'Pi': 'Π',
    'Rho': 'Ρ', 'Sigma': 'Σ', 'Tau': 'Τ', 'Upsilon': 'Υ',
    'Phi': 'Φ', 'Chi': 'Χ', 'Psi': 'Ψ', 'Omega': 'Ω',
    
    # brackets
    'lfloor': '⌊', 'rfloor': '⌋', 'lceil': '⌈', 'rceil': '⌉',
    'langle': '⟨', 'rangle': '⟩', 'lgroup': '⟮', 'rgroup': '⟯',
    'llangle': '⦉', 'rrangle': '⦊', 'llbracket': '⟦', 'rrbracket': '⟧',
    'llparenthesis': '⦇', 'rrparenthesis': '⦈',
    
    'infty': '∞', 'infinity': '∞','aleph': 'ℵ', 'complement': '∁',
    'backepsilon': '∍', 'eth': 'ð', 'Finv': 'Ⅎ',
    'Im': 'ℑ', 'ell': 'ℓ', 'mho': '℧', 'wp': '℘', 'Re': 'ℜ', 'circledS': 'Ⓢ',
    
    # equality
    'neq': '≠', 'leq': '≤', 'geq': '≥', 'approx': '≈', 'le': '≤', 'ge': '≥',
    'cong': '≅', 'equiv': '≡', 'propto': '∝', 'sim': '∼',
    'simeq': '≃', 'asymp': '≍', 'doteq': '≐', 'prec': '≺',
    'succ': '≻', 'preceq': '≼', 'succeq': '≽', 'll': '≪',
    'gg': '≫', 'subset': '⊂', 'supset': '⊃', 'subseteq': '⊆',
    'supseteq': '⊇', 'sqsubset': '⊏', 'sqsupset': '⊐',
    'sqsubseteq': '⊑', 'sqsupseteq': '⊒', 'in': '∈',
    'ni': '∋', 'notin': '∉', 'propto': '∝', 'vdash': '⊢',
    'dashv': '⊣', 'models': '⊨', 'perp': '⊥', 'mid': '∣',
    'parallel': '∥', 'bowtie': '⋈', 'smile': '⌣', 'frown': '⌢',
    'vdots': '⋮', 'cdots': '⋯', 'ldots': '…', 'ddots': '⋱',
    'because': '∵', 'therefore': '∴', 'angle': '∠',
    'measuredangle': '∡', 'sphericalangle': '∢',
    
    # sqrt
    'sqrt': '√',
    
    # calc
    'pm': '±', 'mp': '∓', 'times': '×', 'div': '÷',
    'cdot': '·', 'ast': '∗', 'star': '⋆', 'circ': '∘',
    'bullet': '∙', 'oplus': '⊕', 'ominus': '⊖', 'otimes': '⊗',
    'oslash': '⊘', 'odot': '⊙', 'bigcirc': '◯', 'dagger': '†',
    'ddagger': '‡', 'amalg': '⨿', 'cap': '∩', 'cup': '∪',
    'uplus': '⊎', 'sqcap': '⊓', 'sqcup': '⊔', 'vee': '∨',
    'wedge': '∧', 'diamond': '⋄', 'bigtriangleup': '△',
    'bigtriangledown': '▽', 'triangleleft': '◁',
    'triangleright': '▷', 'triangle': '▵', 'triangledown': '▿',
    'trianglelefteq': '⊴', 'trianglerighteq': '⊵',
    
    # logic
    'land': '∧', 'lor': '∨', 'lnot': '¬', 'forall': '∀',
    'exists': '∃', 'nexists': '∄', 'emptyset': '∅',
    'varnothing': '∅', 'nabla': '∇', 'partial': '∂',
    
    # set
    'in': '∈', 'notin': '∉', 'subset': '⊂', 'subseteq': '⊆',
    'supset': '⊃', 'supseteq': '⊇', 'setminus': '∖',
    
    # induction
    'therefore': '∴', 'because': '∵',
    
    # arrow
    'to': '→', 'gets': '←', 'leftrightarrow': '↔',
    'uparrow': '↑', 'downarrow': '↓', 'updownarrow': '↕',
    'mapsto': '↦', 'longmapsto': '⟼', 'hookleftarrow': '↩',
    'hookrightarrow': '↪', 'leftharpoonup': '↼',
    'rightharpoonup': '⇀', 'leftharpoondown': '↽',
    'rightharpoondown': '⇁', 'rightleftharpoons': '⇌',
    'leftrightharpoons': '⇋', 'rightleftharpoons': '⇌',
    'leftrightarrows': '⇆', 'rightleftarrows': '⇄',
    'upharpoonright': '↾', 'upharpoonleft': '↿',
    'Rightarrow': '⇒', 'Leftarrow': '⇐', 'Leftrightarrow': '⇔',
    'Uparrow': '⇑', 'Downarrow': '⇓', 'Updownarrow': '⇕',
    'Rrightarrow': '⇛', 'Lleftarrow': '⇚', 'leadsto': '↝',
    'implies': '⇒', 'iff': '⇔', 'upuparrows': '⇈',
    
    
    # function
    'sin': 'sin', 'cos': 'cos', 'tan': 'tan', 'cot': 'cot',
    'csc': 'csc', 'sec': 'sec', 'sinh': 'sinh', 'cosh': 'cosh',
    'tanh': 'tanh', 'coth': 'coth', 'csch': 'csch', 'sech': 'sech',
    'arcsin': 'arcsin', 'arccos': 'arccos', 'arctan': 'arctan',
    'arccot': 'arccot', 'arccsc': 'arccsc', 'arcsec': 'arcsec',
    'arsinh': 'arsinh', 'arcosh': 'arcosh', 'artanh': 'artanh',
    'arcoth': 'arcoth', 'arcsch': 'arcsch', 'arsech': 'arsech',
    'lim': 'lim', 'liminf': 'liminf', 'limsup': 'limsup',
    'max': 'max', 'min': 'min', 'sup': 'sup', 'inf': 'inf',
    'arg': 'arg', 'ker': 'ker', 'deg': 'deg', 'det': 'det',
    'gcd': 'gcd', 'lcm': 'lcm', 'Pr': 'Pr', 'varliminf': 'varliminf',
    'varlimsup': 'varlimsup', 'varinjlim': 'varinjlim',
    'varprojlim': 'varprojlim', 'hom': 'hom', 'dim': 'dim', 'mod': 'mod',
    'ln': 'ln', 'log': 'log', 'exp': 'exp',
    
    # other
    'sum': '∑', 'prod': '∏', 'int': '∫', 'oint': '∮',
}

up_map = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
    'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
    'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
    'A': 'ᴬ', 'B': 'ᴮ', 'C': 'ᶜ', 'D': 'ᴰ', 'E': 'ᴱ',
    'F': 'ᶠ', 'G': 'ᴳ', 'H': 'ᴴ', 'I': 'ᴵ', 'J': 'ᴶ',
    'K': 'ᴷ', 'L': 'ᴸ', 'M': 'ᴹ', 'N': 'ᴺ', 'O': 'ᴼ',
    'P': 'ᴾ', 'R': 'ᴿ', 'S': 'ˢ', 'T': 'ᵀ', 'U': 'ᵁ',
    'V': 'ⱽ', 'W': 'ᵂ', 'X': 'ˣ', 'Y': 'ʸ', 'Z': 'ᶻ',
    'α': 'ᵅ', 'β': 'ᵝ', 'γ': 'ᵞ', 'δ': 'ᵟ', 'ε': 'ᵋ',
    'θ': 'ᶿ', 'ι': 'ᶥ', 'φ': 'ᶲ', 'χ': 'ᵡ', 'ψ': 'ᵠ',
}

down_map = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
    'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
    'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
    'v': 'ᵥ', 'x': 'ₓ', 'β': 'ᵦ', 'γ': 'ᵧ', 'ρ': 'ᵨ',
    'φ': 'ᵩ', 'χ': 'ᵪ',
}

mathbb_map = {
    'A': '𝔸', 'B': '𝔹', 'C': 'ℂ', 'D': '𝔻', 'E': '𝔼',
    'F': '𝔽', 'G': '𝔾', 'H': 'ℍ', 'I': '𝕀', 'J': '𝕁',
    'K': '𝕂', 'L': '𝕃', 'M': '𝕄', 'N': 'ℕ', 'O': '𝕆',
    'P': 'ℙ', 'Q': 'ℚ', 'R': 'ℝ', 'S': '𝕊', 'T': '𝕋',
    'U': '𝕌', 'V': '𝕍', 'W': '𝕎', 'X': '𝕏', 'Y': '𝕐',
    'Z': 'ℤ',
    'a': '𝕒', 'b': '𝕓', 'c': '𝕔', 'd': '𝕕', 'e': '𝕖',
    'f': '𝕗', 'g': '𝕘', 'h': '𝕙', 'i': '𝕚', 'j': '𝕛',
    'k': '𝕜', 'l': '𝕝', 'm': '𝕞', 'n': '𝕟', 'o': '𝕠',
    'p': '𝕡', 'q': '𝕢', 'r': '𝕣', 's': '𝕤', 't': '𝕥',
    'u': '𝕦', 'v': '𝕧', 'w': '𝕨', 'x': '𝕩', 'y': '𝕪',
    'z': '𝕫',
    '0': '𝟘', '1': '𝟙', '2': '𝟚', '3': '𝟛', '4': '𝟜',
    '5': '𝟝', '6': '𝟞', '7': '𝟟', '8': '𝟠', '9': '𝟡',
}

mathit_map = {
    'A': '𝐴', 'B': '𝐵', 'C': '𝐶', 'D': '𝐷', 'E': '𝐸',
    'F': '𝐹', 'G': '𝐺', 'H': '𝐻', 'I': '𝐼', 'J': '𝐽',
    'K': '𝐾', 'L': '𝐿', 'M': '𝑀', 'N': '𝑁', 'O': '𝑂',
    'P': '𝑃', 'Q': '𝑄', 'R': '𝑅', 'S': '𝑆', 'T': '𝑇',
    'U': '𝑈', 'V': '𝑉', 'W': '𝑊', 'X': '𝑋', 'Y': '𝑌', 
    'Z': '𝑍',
    'a': '𝑎', 'b': '𝑏', 'c': '𝑐', 'd': '𝑑', 'e': '𝑒',
    'f': '𝑓', 'g': '𝑔', 'h': 'ℎ', 'i': '𝑖', 'j': '𝑗',
    'k': '𝑘', 'l': '𝑙', 'm': '𝑚', 'n': '𝑛', 'o': '𝑜',
    'p': '𝑝', 'q': '𝑞', 'r': '𝑟', 's': '𝑠', 't': '𝑡',
    'u': '𝑢', 'v': '𝑣', 'w': '𝑤', 'x': '𝑥', 'y': '𝑦',
    'z': '𝑧',
}

mathcal_map = {
    'A': '𝒜', 'B': 'ℬ', 'C': '𝒞', 'D': '𝒟', 'E': 'ℰ',
    'F': 'ℱ', 'G': '𝒢', 'H': 'ℋ', 'I': 'ℐ', 'J': '𝒥',
    'K': '𝒦', 'L': 'ℒ', 'M': 'ℳ', 'N': '𝒩', 'O': '𝒪',
    'P': '𝒫', 'Q': '𝒬', 'R': 'ℛ', 'S': '𝒮', 'T': '𝒯',
    'U': '𝒰', 'V': '𝒱', 'W': '𝒲', 'X': '𝒳', 'Y': '𝒴',
    'Z': '𝒵',
    'a': '𝒶', 'b': '𝒷', 'c': '𝒸', 'd': '𝒹', 'e': 'ℯ',
    'f': '𝒻', 'g': 'ℊ', 'h': '𝒽', 'i': '𝒾', 'j': '𝒿',
    'k': '𝓀', 'l': '𝓁', 'm': '𝓂', 'n': '𝓃', 'o': 'ℴ',
    'p': '𝓅', 'q': '𝓆', 'r': '𝓇', 's': '𝓈', 't': '𝓉',
    'u': '𝓊', 'v': '𝓋', 'w': '𝓌', 'x': '𝓍', 'y': '𝓎',
    'z': '𝓏',
}

class MarkdownContext:
    """Manages the console render state."""

    def __init__(
        self,
        console: Console,
        options: ConsoleOptions,
        style: Style,
        inline_code_lexer: str | None = None,
        inline_code_theme: str = "monokai",
    ) -> None:
        self.console = console
        self.options = options
        self.style_stack: StyleStack = StyleStack(style)
        self.stack: Stack[MarkdownElement] = Stack()

        self._syntax: Syntax | None = None
        if inline_code_lexer is not None:
            self._syntax = Syntax("", inline_code_lexer, theme=inline_code_theme)

    @property
    def current_style(self) -> Style:
        """Current style which is the product of all styles on the stack."""
        return self.style_stack.current

    def on_text(self, text: str, node_type: str) -> None:
        """Called when the parser visits text."""
        if node_type in {"fence", "code_inline"} and self._syntax is not None:
            highlight_text = self._syntax.highlight(text)
            highlight_text.rstrip()
            self.stack.top.on_text(
                self, Text.assemble(highlight_text, style=self.style_stack.current)
            )
        elif node_type in {"math_inline"}:
            def replace_symble(match):
                return greek_map.get(match.group(1), match.group(0))
            text = re.sub(r'\\([a-zA-Z]+)', replace_symble, text)
            def replace_pow(match):
                rpl, is_succ = '', True
                for c in match.group(1).strip('{}'):
                    if up_map.get(c) is None:
                        is_succ = False
                    else:
                        rpl += up_map[c]
                return rpl if is_succ else match.group(0)
            up_str = '['+''.join(up_map.keys())+']'
            text = re.sub(rf'\^({up_str}|\{{{up_str}\}}+)', replace_pow, text)
            
            def replace_down(match):
                rpl, is_succ = '', True
                for c in match.group(1).strip('{}'):
                    if down_map.get(c) is None:
                        is_succ = False
                    else:
                        rpl += down_map[c]
                return rpl if is_succ else match.group(0)
            down_str = '['+''.join(down_map.keys())+']'
            text = re.sub(rf'_({down_str}|\{{{down_str}+\}})', replace_down, text)
            
            def replace_text(match):
                return match.group(1)
            text = re.sub(r'\\text\{(.+?)\}', replace_text, text)
            def replace_mathbb(match):
                rpl = ''
                for c in match.group(1):
                    rpl += mathbb_map.get(c, c)
                return rpl
            text = re.sub(r'\\mathbb\{(.+?)\}', replace_mathbb, text)
            def replace_mathit(match):
                rpl = ''
                for c in match.group(1):
                    rpl += mathit_map.get(c, c)
                return rpl
            text = re.sub(r'\\mathit\{(.+?)\}', replace_mathit, text)
            def replace_mathcal(match):
                rpl = ''
                for c in match.group(1):
                    rpl += mathcal_map.get(c, c)
                return rpl
            text = re.sub(r'\\mathcal\{(.+?)\}', replace_mathcal, text)
            def replace_mathbf(match):
                return match.group(1)
            text = re.sub(r'\\mathbf\{(.+?)\}', replace_mathbf, text)
            def replace_mathrm(match):
                return match.group(1)
            text = re.sub(r'\\mathrm\{(.+?)\}', replace_mathrm, text)
            text = re.sub(r'\\([{}()\[\],])', '\\1', text)
            self.stack.top.on_text(self, Text(text, style="markdown.math"))
        else:
            self.stack.top.on_text(self, text)

    def enter_style(self, style_name: str | Style) -> Style:
        """Enter a style context."""
        style = self.console.get_style(style_name, default="none")
        self.style_stack.push(style)
        return self.current_style

    def leave_style(self) -> Style:
        """Leave a style context."""
        style = self.style_stack.pop()
        return style

class Markdown(JupyterMixin):
    """A Markdown renderable.

    Args:
        markup (str): A string containing markdown.
        code_theme (str, optional): Pygments theme for code blocks. Defaults to "monokai". See https://pygments.org/styles/ for code themes.
        justify (JustifyMethod, optional): Justify value for paragraphs. Defaults to None.
        style (Union[str, Style], optional): Optional style to apply to markdown.
        hyperlinks (bool, optional): Enable hyperlinks. Defaults to ``True``.
        inline_code_lexer: (str, optional): Lexer to use if inline code highlighting is
            enabled. Defaults to None.
        inline_code_theme: (Optional[str], optional): Pygments theme for inline code
            highlighting, or None for no highlighting. Defaults to None.
    """

    elements: ClassVar[dict[str, type[MarkdownElement]]] = {
        "paragraph_open": Paragraph,
        "heading_open": Heading,
        "fence": CodeBlock,
        "code_block": CodeBlock,
        "blockquote_open": BlockQuote,
        "hr": HorizontalRule,
        "bullet_list_open": ListElement,
        "ordered_list_open": ListElement,
        "list_item_open": ListItem,
        "image": ImageItem,
        "table_open": TableElement,
        "tbody_open": TableBodyElement,
        "thead_open": TableHeaderElement,
        "tr_open": TableRowElement,
        "td_open": TableDataElement,
        "th_open": TableDataElement
    }

    inlines = {"em", "strong", "code", "s", "math"}

    def __init__(
        self,
        markup: str,
        code_theme: str = "monokai",
        justify: JustifyMethod | None = None,
        style: str | Style = "none",
        hyperlinks: bool = True,
        inline_code_lexer: str | None = None,
        inline_code_theme: str | None = None,
    ) -> None:
        parser = MarkdownIt().use(
            plugin=texmath_plugin, delimiters='brackets'
        ).enable("strikethrough").enable("table")
        self.markup = markup
        self.parsed = parser.parse(markup)
        self.code_theme = code_theme
        self.justify: JustifyMethod | None = justify
        self.style = style
        self.hyperlinks = hyperlinks
        self.inline_code_lexer = inline_code_lexer
        self.inline_code_theme = inline_code_theme or code_theme

    def _flatten_tokens(self, tokens: Iterable[Token]) -> Iterable[Token]:
        """Flattens the token stream."""
        for token in tokens:
            is_fence = token.type == "fence"
            is_image = token.tag == "img"
            if token.children and not (is_image or is_fence):
                yield from self._flatten_tokens(token.children)
            else:
                yield token

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render markdown to the console."""
        style = console.get_style(self.style, default="none")
        options = options.update(height=None)
        context = MarkdownContext(
            console,
            options,
            style,
            inline_code_lexer=self.inline_code_lexer,
            inline_code_theme=self.inline_code_theme,
        )
        tokens = self.parsed
        inline_style_tags = self.inlines
        new_line = False
        _new_line_segment = Segment.line()

        for token in self._flatten_tokens(tokens):
            node_type = token.type
            tag = token.tag

            entering = token.nesting == 1
            exiting = token.nesting == -1
            self_closing = token.nesting == 0

            if node_type == "text":
                context.on_text(token.content, node_type)
            elif node_type == "hardbreak":
                context.on_text("\n", node_type)
            elif node_type == "softbreak":
                context.on_text(" ", node_type)
            elif node_type == "link_open":
                href = str(token.attrs.get("href", ""))
                if self.hyperlinks:
                    link_style = console.get_style("markdown.link_url", default="none")
                    link_style += Style(link=href)
                    context.enter_style(link_style)
                else:
                    context.stack.push(Link.create(self, token))
            elif node_type == "link_close":
                if self.hyperlinks:
                    context.leave_style()
                else:
                    element = context.stack.pop()
                    assert isinstance(element, Link)
                    link_style = console.get_style("markdown.link", default="none")
                    context.enter_style(link_style)
                    context.on_text(element.text.plain, node_type)
                    context.leave_style()
                    context.on_text(" (", node_type)
                    link_url_style = console.get_style(
                        "markdown.link_url", default="none"
                    )
                    context.enter_style(link_url_style)
                    context.on_text(element.href, node_type)
                    context.leave_style()
                    context.on_text(")", node_type)
            elif (
                tag in inline_style_tags
                and node_type != "fence"
                and node_type != "code_block"
            ):
                if entering:
                    # If it's an opening inline token e.g. strong, em, etc.
                    # Then we move into a style context i.e. push to stack.
                    context.enter_style(f"markdown.{tag}")
                elif exiting:
                    # If it's a closing inline style, then we pop the style
                    # off of the stack, to move out of the context of it...
                    context.leave_style()
                else:
                    # If it's a self-closing inline style e.g. `code_inline`
                    context.enter_style(f"markdown.{tag}")
                    if token.content:
                        context.on_text(token.content, node_type)
                    context.leave_style()
            else:
                # Map the markdown tag -> MarkdownElement renderable
                element_class = self.elements.get(token.type) or UnknownElement
                element = element_class.create(self, token)

                if entering or self_closing:
                    context.stack.push(element)
                    element.on_enter(context)

                if exiting:  # CLOSING tag
                    element = context.stack.pop()

                    should_render = not context.stack or (
                        context.stack
                        and context.stack.top.on_child_close(context, element)
                    )

                    if should_render:
                        if new_line:
                            yield _new_line_segment

                        yield from console.render(element, context.options)
                elif self_closing:  # SELF-CLOSING tags (e.g. text, code, image)
                    context.stack.pop()
                    text = token.content
                    if text is not None:
                        element.on_text(context, text)

                    should_render = (
                        not context.stack
                        or context.stack
                        and context.stack.top.on_child_close(context, element)
                    )
                    if should_render:
                        yield from console.render(element, context.options)

                if exiting or self_closing:
                    element.on_leave(context)
                    new_line = element.new_line


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Render Markdown to the console with Rich"
    )
    parser.add_argument(
        "path",
        metavar="PATH",
        help="path to markdown file, or - for stdin",
    )
    parser.add_argument(
        "-c",
        "--force-color",
        dest="force_color",
        action="store_true",
        default=None,
        help="force color for non-terminals",
    )
    parser.add_argument(
        "-t",
        "--code-theme",
        dest="code_theme",
        default="monokai",
        help="pygments code theme",
    )
    parser.add_argument(
        "-i",
        "--inline-code-lexer",
        dest="inline_code_lexer",
        default=None,
        help="inline_code_lexer",
    )
    parser.add_argument(
        "-y",
        "--hyperlinks",
        dest="hyperlinks",
        action="store_true",
        help="enable hyperlinks",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        dest="width",
        default=None,
        help="width of output (default will auto-detect)",
    )
    parser.add_argument(
        "-j",
        "--justify",
        dest="justify",
        action="store_true",
        help="enable full text justify",
    )
    parser.add_argument(
        "-p",
        "--page",
        dest="page",
        action="store_true",
        help="use pager to scroll output",
    )
    args = parser.parse_args()

    from rich.console import Console

    if args.path == "-":
        markdown_body = sys.stdin.read()
    else:
        with open(args.path, encoding="utf-8") as markdown_file:
            markdown_body = markdown_file.read()

    markdown = Markdown(
        markdown_body,
        justify="full" if args.justify else "left",
        code_theme=args.code_theme,
        hyperlinks=args.hyperlinks,
        inline_code_lexer=args.inline_code_lexer,
    )
    if args.page:
        import io
        import pydoc

        fileio = io.StringIO()
        console = Console(
            file=fileio, force_terminal=args.force_color, width=args.width
        )
        console.print(markdown)
        pydoc.pager(fileio.getvalue())

    else:
        console = Console(
            force_terminal=args.force_color, width=args.width, record=True
        )
        console.print(markdown)
