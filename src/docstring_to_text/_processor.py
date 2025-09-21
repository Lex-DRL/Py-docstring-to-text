# encoding: utf-8
"""
The main processing :class:`DocstringToText` class - in its own submodule for readability.
"""

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U

from contextlib import contextmanager as _contextmanager
import re as _re

from .___package_meta import VERSION

from .__dataclass import *
from .__parsed_line import *


_t_re_match_result = _O[_re.Match[str]]
_t_re_match_func = _C[[str], _t_re_match_result]

IN_BULLETS = '-*∙•⬤⦾⦿◉◦○➲‣►▪■◼➣➢➤★'  # Intentionally exclude long dashes by default - to preserve dialogues.
IN_BULLETS_WITH_LONG_DASHES = f'—–{IN_BULLETS}'
OUT_BULLETS = '•○■►★'

T = _t.TypeVar('T')

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


def _binary_indent(indent_spaces: int) -> int:
	"""Reduce any indent to 1 or 0. Negative values clamped to 0."""
	return 1 if indent_spaces > 0 else 0


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
	in_bullets: _U[_t.Iterable[str], str] = _field(default=IN_BULLETS)
	out_bullets: _U[_t.Iterable[str], str, None] = _field(default=OUT_BULLETS)
	tab_size: int = 4

	# Internal "private" fields. Dataclasses with true private fields (dunder attrs)
	# is a real pain to work with. So let's use protected instead:

	_common_block_spaces_to_tabs: _C[[int], int] = _field(default=_binary_indent, init=False, repr=False)

	_out_bullets_n: int = _field(default=1, init=False, repr=False)
	# Cached func to use for retrieving the output bullet in the final line formatting:
	_out_bullet_get: _O[_C[[ParsedLine, int], str]] = _field(default=None, init=False, repr=False)

	_re_bullet_match: _O[_t_re_match_func] = _field(default=None, init=False, repr=False)

	# Not changed per instance, but still turned to arguments,
	# because slotted argument access is faster than searching a variable in outer scope
	_re_indent_match: _t_re_match_func = _field(default=_re_indent_match_, init=False, repr=False)
	_re_indent_parse: _t_re_match_func = _field(default=_re_indent_parse_, init=False, repr=False)
	_re_number_match: _t_re_match_func = _field(default=_re_number_match_, init=False, repr=False)

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

		common_block_spaces_to_tabs: _C[[int], int] = (
			_binary_indent if self.minimize_indents else self.__common_block_spaces_to_tabs__round_full_tabs
		)

		tab_size = self.tab_size
		if not(isinstance(tab_size, int) and tab_size > 0):
			tab_size = int(tab_size)
			tab_size = max(1, tab_size)

		in_bullets = _re.escape(in_bullets)
		re_bullet_match: _t_re_match_func = _re.compile(
			f'([{in_bullets}]+)'
			r'(?:'
			r'\s+(.*?)'  # Must have at least one space after bullet to prevent matching `\t*bold* text`...
			r'|'
			r'\s*'  # ... or the bullet has to be the only non-whitespace characters on the line
			r')$'
		).match

		for name, value in [
			('in_bullets', in_bullets),
			('out_bullets', out_bullets),
			('_out_bullets_n', out_bullets_n),
			('_out_bullet_get', out_bullet_get_f),
			('_common_block_spaces_to_tabs', common_block_spaces_to_tabs),
			('tab_size', tab_size),
			('_re_bullet_match', re_bullet_match),
		]:
			# Well-known workaround to initialize attributes on frozen instance:
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

	def __common_block_spaces_to_tabs__round_full_tabs(self, indent_spaces: int) -> int:
		"""Converts space-indents to tabs, when :attr:`minimize_indents` is ``False``.

		Might be assigned to :attr:`_common_block_spaces_to_tabs`.
		"""
		if indent_spaces < 1:
			return 0
		tabs_f = float(indent_spaces) / self.tab_size
		return max(int(tabs_f + 0.4999), 1)

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

	@staticmethod
	def __extract_first_sub_block(pending_lines: _t.List[ParsedLine]) -> _t.Tuple[bool, _t.List[ParsedLine], _t.List[ParsedLine]]:
		"""Distinct function for pass 2:

		Assuming the given pending block is:
			1. already un-indented
			2. non-empty
			3. isn't just a bunch of empty and zero-indent text lines
		... split it into two parts:
			- The first distinct chunk.
			- The rest of the lines, still unclassified (pending).

		The distinct chunk is one of:
			- If the pending block starts with indented lines, all the lines before the first unindented one.
			- If starts with zero indent, all the lines at this level and with this type till the first change.
			- If all the lines are either empty or have the same type and indent, the whole pending block.

		So, the extracted first chunk is either uniform or has sub-indents,
		which is what the first returned ``bool`` indicates: ``True`` = just a sub-indent for further classification.
		"""
		assert bool(pending_lines)
		first_real_line_with_zero_indent_i = next(
			i for i, x in enumerate(pending_lines)
			if x.indent == 0 and not x.is_empty
		)
		if first_real_line_with_zero_indent_i > 0:
			first_chunk: _t.List[ParsedLine] = pending_lines[:first_real_line_with_zero_indent_i]
			# But we might start from non-first line simply because there were some non-empty ones in the beginning.
			# So, to exclude such case...
			if not all(x.is_empty for x in first_chunk):
				return True, first_chunk, pending_lines[first_real_line_with_zero_indent_i:]

		first_chunk: _t.List[ParsedLine] = []
		remaining_lines: _t.List[ParsedLine] = []

		first_real_line = pending_lines[first_real_line_with_zero_indent_i]
		chunk_type = first_real_line.block_type()
		first_chunk_append = first_chunk.append

		lines_iter = iter(pending_lines)
		for line in lines_iter:
			if line.is_empty or (line.indent == 0 and line.block_type() == chunk_type):
				first_chunk_append(line)
				continue
			remaining_lines.append(line)
			remaining_lines.extend(lines_iter)
			break

		return False, first_chunk, remaining_lines

	def __pass2_change_indents_to_tabs(self, joined_blocks: _t.List[ParsedLine]) -> _t.List[ParsedLine]:
		"""Second pass on list of :class:`ParsedLine`:

		Turn initial space-indents into proper tabs: that's what :attr:`ParsedLine.indent`
		means now. Again, the :class:`ParsedLine` instances are mutated in-place, but the
		returned list itself is new.

		Prerequisites:
			- first pass: all the items are already joined into paragraph blocks;
			- *(expected first pass output)* the indents in input list are measured **IN SPACES**.
		"""
		output: _t.List[ParsedLine] = []

		pending_stack: _t.List[StackLevelBlock] = [StackLevelBlock(pending_lines=joined_blocks)]

		# Local-scope vars to get rid of 'dot' operator in the loop:
		output_extend = output.extend
		pending_stack_append = pending_stack.append
		pending_stack_pop = pending_stack.pop
		common_spaces_to_tabs = self._common_block_spaces_to_tabs
		extract_first_sub_block = self.__extract_first_sub_block
		unindent = ParsedLine.unindent

		def flush_to_output(lines_list: _t.List[ParsedLine], tab_indent, list_level):
			for line in lines_list:
				line.indent = tab_indent
				line.list_level = list_level
			output_extend(lines_list)

		while pending_stack:
			active_block: StackLevelBlock = pending_stack_pop()
			pending_lines: _t.List[ParsedLine] = active_block.pending_lines
			if not pending_lines:
				continue

			# Warning! In-place line mutation... but thanks to the stack design
			# + pop() at the very first step in the loop, we either have zero
			# offset (thus, no mutation), or recreate a new stack-level instance.
			# Either way, each line is always owned by a single list of pending
			# lines.
			block_common_indent_spaces = unindent(pending_lines)

			# Case: just offset
			if block_common_indent_spaces > 0:
				# We have a shared indent across the whole block.
				# Update the stack and go to the next iteration.
				new_list_level = active_block.list_level
				block_common_indent_tabs = common_spaces_to_tabs(block_common_indent_spaces)
				if active_block.in_list != BlockType.Indent:
					# The active block (before un-indent) was a list.
					# We need to prepend the new block in the stack
					# with the same "parent" indent, but no lines:
					pending_stack_append(active_block.copy(pending_lines=None))
					new_list_level += block_common_indent_tabs
				pending_stack_append(
					active_block.copy(
						indent_spaces_abs=active_block.indent_spaces_abs + block_common_indent_spaces,
						indent_spaces_rel=block_common_indent_spaces,
						indent_tabs_abs=active_block.indent_tabs_abs + block_common_indent_tabs,
						list_level=new_list_level,
						# Even if we're in list, this block is just an indent:
						block_type=BlockType.Indent,
					)
				)
				continue

			assert block_common_indent_spaces == 0 and pending_lines

			tab_indent = active_block.indent_tabs_abs
			list_level = active_block.list_level

			# Case: the lowest-level, just-a-text block:
			if all(x.is_empty or (x.indent == 0 and not x.is_list) for x in pending_lines):
				flush_to_output(pending_lines, tab_indent, list_level)
				continue

			is_sub_indent, first_chunk, pending_lines = extract_first_sub_block(pending_lines)
			assert bool(first_chunk)

			if is_sub_indent or pending_lines:
				new_pending_parent_block = active_block.copy(pending_lines=None if not pending_lines else pending_lines)
				pending_stack_append(new_pending_parent_block)

			if is_sub_indent:
				pending_stack_append(active_block.copy(pending_lines=first_chunk))

			if not is_sub_indent:
				flush_to_output(first_chunk, tab_indent, list_level)
				continue

			pending_stack_append(active_block.copy(pending_lines=first_chunk))
			pass  # while

		assert not pending_stack
		return output

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
		lines = [parse_line(l) for l in text.splitlines()]
		common_indent_in_spaces, lines = self.__pass1_join_raw_blocks(lines)
		lines = self.__pass2_change_indents_to_tabs(lines)
