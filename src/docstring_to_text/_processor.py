# encoding: utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
The main processing :class:`DocstringToText` class - in its own submodule for readability.
"""

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U

from contextlib import contextmanager as _contextmanager
import re as _re

from .___package_meta import VERSION

from .__dataclasses_compat import *
from .__internal_classes import *
from .__internal_spaces_to_tabs import SpaceToTabsConverter as _SpaceToTabsConverter


_t_re_match_result = _O[_re.Match[str]]
_t_re_match_func = _C[[str], _t_re_match_result]

IN_BULLETS = '-*∙•⬤⦾⦿◉◦○➲‣►▪■◼➣➢➤★'  # Intentionally exclude long dashes by default - to preserve dialogues.
IN_BULLETS_WITH_LONG_DASHES = f'—–{IN_BULLETS}'
OUT_BULLETS = '•○■►★'

_re_indent_match_: _t_re_match_func = _re.compile(
	r'(\s*)'
	r'(.*?)$'
).match
_re_indent_parse_: _t_re_match_func = _re.compile(
	r'(\t*)'
	r'([^\t]*)'
	r'(.*?)$'
).match
_re_number_match_: _t_re_match_func = _re.compile(
	r"("  # First group: the numeration
	r"(?:"  # The optional multipart prefix, that might repeat
	r"\s*"  # The passed string already doesn't have spaces in the beginning, but `1. 2.` / `1) 2)` might have
	r"(?:\d+|[a-zA-Z])"  # The number or a single latin letter
	r"[_'`´,.:)~—–-]+"  # Any kind of immediate separators: `1.`, `1)`, etc.
	r")*" # ... the "might repeat" part (or might be absent)
	r"\s*"    # Still inside the group...
	r"(?:\d+|[a-zA-Z])"  # ... the last part of the number, it's required...
	r"[.:)]+"  # ... and must end with a much more restricted set of separator characters.
	r")\s*"  # First group ends, optional space after.
	r'(.*?)$'  # Second part: the actual text
).match
# _re_number_match_('123.\n456.789. \tqqq').groups()
# _re_number_match_('123~456`789:qqq').groups()
# _re_number_match_('a.b.c. qqq').groups()
# _re_number_match_('a.b.c.qqq').groups()
# _re_number_match_('a-b-c)qqq').groups()
# _re_number_match_("a`b'c~d: qqq").groups()
# _re_number_match_('aa-bb-cc.qqq').groups()  # must fail: double letter
# _re_number_match_('a-bb-cc.qqq').groups()  # must fail: wrong end after 'a'
# _re_number_match_('a)bb-cc.qqq').groups()
# _re_number_match_("1-a,b... qqq").groups()


@_contextmanager
def _temp_iter(iterable: _t.Iterable[T]) -> _t.Generator[_t.Iterator[T], _A, None]:
	"""Create a temporary iterator that exists only inside the ``with`` block."""
	try:
		iterator = iter(iterable)
		yield iterator
	finally:
		pass


# ==========================================================


@_dataclass(frozen=True, **_dataclass_slots_and_kw_only_args)
class DocstringToText:
	"""Converts docstrings into a clean text (creating proper paragraphs and indents).

	:class:`DocstringToText` is a "processor"-style class:
	think of its instance as of a set of functions, which have shared
	"global-like" settings and which you configure only once for a
	specific docstring style.

	It's also implemented as a "multiton": multiple instances created
	with the same set of attributes are actually the same single instance.

	Features
	--------

	-
		All the redundant trailing spaces at the end of a line
		are always removed. There's intentionally no option for that.
	-
		A line, which starts (after indent) with either of: ``-``, ``*``,
		``•``, and many other unicode characters (or their sequence),
		is recognized as a bulleted list item.

		-
			Most common characters are detected by default
			(see the module's :obj:`IN_BULLETS`).
		- This character set is configurable.
	-
	 The bulleted list can be converted to another set of
	 level-specific bullet characters, or preserved as-is.
	-
		A line starting with "0.", "1. 1.", "2)", "1)3)", "a)", "a. b:"
		"1´1- a. 2~b)", etc. (after indent), is recognized as a numbered list item.
		Numeration itself preserved as-is, to the letter.

	Typical use
	-----------

	Code::

		converter = DocstringToText()  # All the default settings
		converter = DocstringToText(tab_size=4)  # The same instance
		converter = DocstringToText(tab_size=5)  # Custom tab size

	How the docstring should look with ``list_with_indent=True``::

		A regular text outside list.
		- A list item
		  that spans multiple lines.
		Another regular text. Empty lines before/after it
		are optional.

		-
		  Another item, also multiline, and formatted as a
		  reST-like block.

		  Second line in the same list item.

	... and with ``list_no_indent=True``::

		A regular text outside list.
		- A list item
		that spans multiple lines.

		Another regular text. This time, you need an empty
		line before it, but the one after is still optional.
		-
		Another item, also multiline, and formatted as a
		reST-like block. But now, without an indent.

	If both are ``True``, your docstring can have either of those, even mixed.

	If both are set to ``False``, then effectively list items can't be
	multiline in the source.

	:ivar indent_empty_lines:
		**Do you want to preserve indents in empty lines?**
		Even if ``True``, they still aren't actually preserved "as-is", but
		are instead re-created according to the block an empty line belongs to.
		If ``False``, all the empty lines are stripped from spaces/tabs completely.
	:ivar minimize_indents:
		When ``True``, any indented block would always offset one tab,
		even if the source text contained many.
		When ``False``, the original indentation preserved exactly. This might be
		useful for nested lists which start for a second level.
	:ivar list_with_indent:
		For list items: whether to consider the lines following after a list item
		as its continuation if they are indented.
		If ``False``, such lines are considered its own block UNDER the item.
	:ivar list_no_indent:
		For list items: whether to consider the lines following after a list item
		as its continuation if they are NOT indented (i.e., at the same level as bullet point).
		If ``False``, such lines are considered its own block AFTER the item.
	:ivar in_bullets:
		Any of the provided characters are considered a bullet point in list.
		Order is independent, no relation to list hierarchy. Hierarchy is detected from indents.
	:ivar out_bullets:
		An optional tuple of bullet characters to convert any bulleted list to.
		So, items starting with ``-`` or ``*`` might be turned into actual bullets: ``•``.
		The multiple values are for indentation levels. For levels deeper than specified,
		the sequence is looped.
	:ivar tab_size:
		The resulting text is converted to tab-only indents, according to this value.
		Using this output, you can easily convert it to whatever indentation characters
		you want.
	"""

	class __InstancePool:
		"""Internal subclass, handling multiton-style pool.

		Made as a nested class, because it's the easiest way to have an
		actually private member at clas level of a dataclass.
		"""
		pool_dict: _t.Dict[tuple, 'DocstringToText'] = dict()

	indent_empty_lines: bool = False
	minimize_indents: bool = True
	list_with_indent: bool = True
	list_no_indent: bool = True
	tab_size: int = 4

	in_bullets: _U[_t.Iterable[str], str] = _field(default=IN_BULLETS)
	out_bullets: _U[_t.Iterable[str], str, None] = _field(default=OUT_BULLETS)

	# Internal "private" fields. Dataclasses with true private fields (dunder attrs)
	# is a real pain to work with. So let's use protected instead:

	_out_bullets_n: int = _field(default=1, init=False, repr=False)
	# Cached func to use for retrieving the output bullet in the final line formatting:
	_out_bullet_get: _O[_C[[ParsedLine, int], str]] = _field(default=None, init=False, repr=False)

	_re_bullet_match: _O[_t_re_match_func] = _field(default=None, init=False, repr=False)

	# Not changed per instance, but still turned to arguments,
	# because slotted argument access is faster than searching a variable in outer scope
	_re_indent_match: _t_re_match_func = _field(default=_re_indent_match_, init=False, repr=False)
	_re_indent_parse: _t_re_match_func = _field(default=_re_indent_parse_, init=False, repr=False)
	_re_number_match: _t_re_match_func = _field(default=_re_number_match_, init=False, repr=False)

	_pass2_change_indents_to_tabs: _C[[_t.List[ParsedLine]], _t.List[ParsedLine]] = _field(
		default=_SpaceToTabsConverter(minimize_indents=True, tab_size=4).convert,
		init=False, repr=False
	)

	def __new__(
		cls, *_,  # Even for pre-Py3.10, enforce keyword-only args
		# For proper IDE hints, explicit list of identical args:
		indent_empty_lines: bool = False,
		minimize_indents: bool = True,
		list_with_indent: bool = True,
		list_no_indent: bool = True,
		in_bullets: _U[_t.Iterable[str], str] = IN_BULLETS,
		out_bullets: _U[_t.Iterable[str], str, None] = OUT_BULLETS,
		tab_size: int = 4,
	) -> 'DocstringToText':
		"""
		Creates a :class:`DocstringToText` class instance, ensuring
		that only one instance with a given set of parameters exist.

		The same object is returned for subsequent calls with the same
		argument values.
		"""
		pool = DocstringToText.__InstancePool.pool_dict
		assert isinstance(pool, dict), f"Internal error - wrong pool type: {pool!r}"

		indent_empty_lines, minimize_indents, list_with_indent, list_no_indent = (
			bool(x) for x in [indent_empty_lines, minimize_indents, list_with_indent, list_no_indent]
		)
		in_bullets = DocstringToText.__init_bullets_attr_to_str(in_bullets)
		out_bullets = DocstringToText.__init_bullets_attr_to_str(out_bullets) if out_bullets else None
		tab_size = max(int(tab_size), 1)

		args_key = (
			indent_empty_lines, minimize_indents, list_with_indent, list_no_indent,
			in_bullets, out_bullets, tab_size
		)
		instance = pool.get(args_key)
		if instance is not None:
			return instance

		# Create an instance only if it doesn't exist:
		instance = object.__new__(cls)
		pool[args_key] = instance
		return instance

	def __post_init__(self):
		# Since the instances are pooled in a multiton manner, we better convert
		# all the args with builtin immutable values to the exact basic types,
		# to prevent some inherited class instances for living forever.
		indent_empty_lines = bool(self.indent_empty_lines)
		minimize_indents = bool(self.minimize_indents)
		list_with_indent = bool(self.list_with_indent)
		list_no_indent = bool(self.list_no_indent)
		tab_size = max(int(self.tab_size), 1)

		in_bullets = self.__init_bullets_attr_to_str(self.in_bullets)
		if not in_bullets:
			in_bullets = self.__init_bullets_attr_to_str(IN_BULLETS)
		if not (
			isinstance(in_bullets, str) and in_bullets
			and not any(x in in_bullets for x in ' \t\n\r')
		):
			raise RuntimeError(
				"Internal error - IN_BULLETS module-level constant in <docstring_to_text> package has "
				f"an invalid value at runtime: {IN_BULLETS!r}"
			)

		out_bullets = self.out_bullets
		out_bullets = self.__init_bullets_attr_to_str(out_bullets) if out_bullets else None
		if not out_bullets:
			out_bullets = None
		if not (
			out_bullets is None or (
				isinstance(out_bullets, str) and out_bullets
				and not any(x in out_bullets for x in ' \t\n\r')
			)
		):
			raise RuntimeError(
				f"Internal error - unexpected value for out_bullets: {out_bullets!r}"
			)

		if out_bullets:
			out_bullets_n = len(out_bullets)
			out_bullet_get_f = self.__out_bullet_get__with_bullet_replacement
		else:
			out_bullets_n = 1
			out_bullet_get_f = self.__out_bullet_get__intact

		in_bullets = _re.escape(in_bullets)
		re_bullet_match: _t_re_match_func = _re.compile(
			f'([{in_bullets}]+)'
			r'(?:'
			r'\s+(.*?)'  # Must have at least one space after bullet to prevent matching `\t*bold* text`...
			r'|'
			r'\s*'  # ... or the bullet has to be the only non-whitespace characters on the line
			r')$'
		).match

		pass2_change_indents_to_tabs_f = self._pass2_change_indents_to_tabs
		if not (minimize_indents and tab_size == 4):
			# Only change it if non-default:
			pass2_change_indents_to_tabs_f = _SpaceToTabsConverter(
				minimize_indents=minimize_indents, tab_size=tab_size
			).convert  # This method is the only thing we need from the `_SpaceToTabsConverter` instance
			# The `_SpaceToTabsConverter` instance itself is already forgotten

		for name, value in [
			('indent_empty_lines', indent_empty_lines),
			('minimize_indents', minimize_indents),
			('list_with_indent', list_with_indent),
			('list_no_indent', list_no_indent),
			('tab_size', tab_size),

			('in_bullets', in_bullets),
			('out_bullets', out_bullets),

			('_out_bullets_n', out_bullets_n),
			('_out_bullet_get', out_bullet_get_f),
			('_re_bullet_match', re_bullet_match),
			('_pass2_change_indents_to_tabs', pass2_change_indents_to_tabs_f),
		]:
			# Well-known workaround to re-initialize attributes on frozen instance:
			object.__setattr__(self, name, value)

	@staticmethod
	def version() -> str:
		"""The module version."""
		return VERSION

	@staticmethod
	def __init_bullets_attr_to_str(seq: _U[_t.Iterable[str], str]) -> str:
		"""Prepare a string of bullet characters as the expected attribute value. Whitespaces removed."""
		# First, join it to a string:
		seq_str = seq if isinstance(seq, str) else ''.join(seq)
		# Then, get rid of any whitespaces and re-join:
		return ''.join(seq_str.split())  # `split()` removes whitespaces

	@staticmethod
	def __out_bullet_get__intact(line: ParsedLine, bullet_level: int) -> str:
		"""Bullet-getting function for :attr:`_out_bullet_get`, used when output bullets are **NOT** provided."""
		return line.bullet

	def __out_bullet_get__with_bullet_replacement(self, line: ParsedLine, bullet_level: int) -> str:
		"""Bullet-getting function for :attr:`_out_bullet_get`, used when :attr:`out_bullets` are provided."""
		i = bullet_level % self._out_bullets_n
		return self.out_bullets[i]

	def __format_line(self, line: ParsedLine, bullet_level: int):
		"""
		When the entire text is already processed into a sequence of final lines
		(so, no further indent changes), this method turns each of them
		into a final line-string. No newline character at the end.
		"""
		indent_full_tabs = int(
			float(max(line.indent, 0)) / self.tab_size + 0.50001
		)
		indent_str = '\t' * indent_full_tabs
		if line.bullet:
			bullet = self._out_bullet_get(line, bullet_level)
			return f"{indent_str}{bullet} {line.text}"
		if line.number:
			return f"{indent_str}{line.number}{line.number_sep} {line.text}"
		return f"{indent_str}{line.text}"

	def __detect_indent(self, indent_str: str) -> int:
		"""Given a pre-extracted part of the line with only tabs and spaces, detect indent (**IN SPACES**)."""
		if not indent_str:
			return 0

		full_tabs = 0
		pending_spaces = 0
		indent_parse_f = self._re_indent_parse
		tab_size = self.tab_size

		# The match function always returns a match, thanks to '*' qualifiers.
		# So do it until nothing's left of the original string:
		while indent_str:
			match = indent_parse_f(indent_str)
			tabs_str, spaces_str, indent_str = match.groups()
			# If any spaces were pending, they're discarded now, because we're guaranteed to have
			# true tabs in all non-first iterations. And those tabs eat pending spaces,
			# which, by definition, are LESS than a single tab.
			pending_spaces = len(spaces_str)
			current_space_tabs = pending_spaces // tab_size
			pending_spaces = pending_spaces % tab_size
			full_tabs += len(tabs_str) + current_space_tabs
		return full_tabs * tab_size + pending_spaces

	def __parse_line(self, line: str) -> ParsedLine:
		"""Initial part of parsing: split a single line into :class:`ParsedLine` object.

		**WARNING**: At this (internal-only) stage, indents are actually measured in spaces,
		contrary to what the attribute docstring for :attr:`ParsedLine.indent` says.
		"""
		line = line.rstrip()
		match = self._re_indent_match(line)
		if not match:
			# Theoretically, '*' qualifier in regex ensures we always match with `_re_indent_match`,
			# but just to be safe...
			return ParsedLine(0, is_empty=True, is_list=False, bullet='', number='', number_sep='', text='')

		indent_str, text = match.groups()
		indent = self.__detect_indent(indent_str)

		match = self._re_bullet_match(text)
		if match:
			groups = match.groups()
			bullet = groups[0]
			text = '' if len(groups) == 1 else groups[1]
			return ParsedLine(indent, is_empty=False, is_list=True, bullet=bullet, number='', number_sep='', text=text)

		match = self._re_number_match(text)
		if match:
			number, sep, text = match.groups()
			return ParsedLine(indent, is_empty=False, is_list=True, bullet='', number=number, number_sep=sep, text=text)
		if not text:
			# Empty line should have 0 as indent:
			ParsedLine(0, is_empty=True, is_list=False, bullet='', number='', number_sep='', text='')
		return ParsedLine(indent, is_empty=False, is_list=False, bullet='', number='', number_sep='', text=text)

	@staticmethod
	def __flush_raw_active_block(pending_block: _t.List[ParsedLine], joined_blocks: _t.List[ParsedLine]):
		"""Utility function for pass 1: Flush a pending block into the list of joined blocks.

		Pending block is the active chunk of text with the same indent.

		:var:`pending_block` list is cleared as a result.
		"""
		if not pending_block:
			return

		block_iter = iter(pending_block)
		first = next(block_iter)  # Used further, beyond assert
		first_id = first.block_id()
		assert all(x.block_id() == first_id for x in block_iter), (
			f"Lines of different block-IDs in the pending block: {pending_block!r}"
		)
		del block_iter
		del first_id

		if first.is_list or first.is_empty:
			# Pending block is a block of sequential empty lines or list items at the same level
			# All the lines need to be passed as-is:
			joined_blocks.extend(pending_block)
			pending_block.clear()
			return

		# A regular text block - join the block
		joined_text = ' '.join(x.text for x in pending_block)
		joined_blocks.append(ParsedLine(first.indent, is_empty=False, text=joined_text))
		pending_block.clear()

	@staticmethod
	def __pass1_join_raw_blocks(parsed_text: _t.List[ParsedLine]) -> _t.Tuple[int, _t.List[ParsedLine]]:
		"""First pass on list of parsed lines: join raw blocks.

		The returned list is new, but common indent is removed in-place,
		by mutating :class:`ParsedLine` instances.

		Raw blocks are just the blocks of the same indent and type.
		For now, we completely ignore joining first list lines with their continuation.
		They will be joined later. For now, our goal is at least turning
		the continuous blocks into single paragraphs (:class:`ParsedLine` items).

		Empty lines break blocks. So, in each sequence of empty lines first one is removed,
		but the remaining ones are preserved as individual items.

		WARNING
		-------
		At this (internal-only) stage, indents are actually measured in spaces,
		contrary to what the attribute docstring for :attr:`ParsedLine.indent` says.

		:return: The removed common indent and the list of initially joined blocks.
		"""
		common_indent = ParsedLine.unindent(parsed_text)

		# This list will get each block joined into a single item.
		# Starting list-item lines are still separate and detached from their continuing block.
		joined_blocks: _t.List[ParsedLine] = list()

		# Scheduled lines for the current block:
		pending_block: _t.List[ParsedLine] = list()
		pending_block_append = pending_block.append

		# Since we simply start a new block on indent/type change, we don't need
		# a full stack yet. Just an active level's indent and mode is enough.
		active_indent = 0
		active_block = BlockType.Indent
		is_after_empty_line = False
		flush_raw_active_block = DocstringToText.__flush_raw_active_block
		for line in parsed_text:
			if line.is_empty:
				if is_after_empty_line:
					pending_block_append(line)
					continue
				# The first empty line after a valid block.
				# Don't add the line itself, but flush the active block and indicate the flag:
				is_after_empty_line = True
				flush_raw_active_block(pending_block, joined_blocks)
				continue
			if is_after_empty_line:
				# We're after an empty line - maybe, after a block of them.
				# But the current line is not empty.
				flush_raw_active_block(pending_block, joined_blocks)
				is_after_empty_line = False
				# ... but stay in the current iteration, no `continue`
			line_indent = line.indent
			line_block = line.block_type()
			if not(line_indent == active_indent and line_block == active_block):
				flush_raw_active_block(pending_block, joined_blocks)
				active_indent = line_indent
				active_block = line_block
			pending_block_append(line)

		return common_indent, joined_blocks

	# Pass 2 is per-instance function, in `_pass2_change_indents_to_tabs`,
	# from _SpaceToTabsConverter.convert

	def __pass3_join_list_headers_with_continuation(self, joined_blocks: _t.List[ParsedLine]) -> _t.List[ParsedLine]:
		"""Third pass on list of :class:`ParsedLine`:

		For each list item, join its first line with the continuation.

		Prerequisites:
			- first pass: all the items are already joined into paragraph blocks;
			- second pass: :attr:`ParsedLine.indent` is measured in tabs.
		"""
		pass

	def __parse_to_blocks(self, text: str) -> _t.List[ParsedLine]:
		parse_line = self.__parse_line
		lines: _t.List[ParsedLine] = [parse_line(l) for l in text.splitlines()]
		common_indent_in_spaces, lines = self.__pass1_join_raw_blocks(lines)
		lines = self._pass2_change_indents_to_tabs(lines)
