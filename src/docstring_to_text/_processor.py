# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
The main processing :class:`DocstringToText` class - in its own submodule for readability.
"""

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U

from collections import deque as _deque
from contextlib import contextmanager as _contextmanager

from .___package_meta import VERSION_TUPLE

from .__dataclasses_compat import *
from .__defaults import *
from .__internal_parsed_line import *
from .__internal_spaces_to_tabs import SpaceToTabsConverter as _SpaceToTabsConverter
from .__regex_line_parse import *


@_contextmanager
def _temp_iter(iterable: _t.Iterable[T]) -> _t.Generator[_t.Iterator[T], _A, None]:
	"""Create a temporary iterator that exists only inside the ``with`` block."""
	try:
		iterator = iter(iterable)
		yield iterator
	finally:
		pass


# ==========================================================


class _ArgsKey(_t.NamedTuple):
	"""A key identifying unique set of :class:`DocstringToText` attributes.

	Used internally for instance pooling and argument cleanup during initialization.
	"""
	indent_empty_lines: bool = False
	minimize_indents: bool = True
	list_with_indent: bool = True
	list_no_indent: bool = True
	tab_size: int = TAB_SIZE
	in_bullets: str = IN_BULLETS
	out_bullets: _O[str] = OUT_BULLETS

	@staticmethod
	def __cleanup_bullets_attr_to_str(seq: _U[_t.Iterable[str], str]) -> str:
		"""Prepare a string of bullet characters as the expected attribute value. Whitespaces removed."""
		# First, join it to a string:
		seq_str = seq if isinstance(seq, str) else ''.join(seq)
		# Then, get rid of any whitespaces and re-join:
		return ''.join(seq_str.split())  # `split()` removes whitespaces

	@classmethod
	def clean_key(
		cls: _t.Type[T],
		indent_empty_lines: bool = False,
		minimize_indents: bool = True,
		list_with_indent: bool = True,
		list_no_indent: bool = True,
		tab_size: int = TAB_SIZE,
		in_bullets: _U[_t.Iterable[str], str] = IN_BULLETS,
		out_bullets: _U[_t.Iterable[str], str, None] = OUT_BULLETS,
	) -> T:
		# Since the instances are pooled in a multiton manner, we better convert
		# all the args with builtin immutable values to the exact basic types,
		# to prevent some inherited class instances for living forever.
		indent_empty_lines = bool(indent_empty_lines)
		minimize_indents = bool(minimize_indents)
		list_with_indent = bool(list_with_indent)
		list_no_indent = bool(list_no_indent)

		in_bullets = cls.__cleanup_bullets_attr_to_str(in_bullets)
		if not in_bullets:
			in_bullets = cls.__cleanup_bullets_attr_to_str(IN_BULLETS)
		if not (
			isinstance(in_bullets, str) and in_bullets
			and not any(x in in_bullets for x in ' \t\n\r')
		):
			raise ValueError(
				"Internal error - IN_BULLETS module-level constant in <docstring_to_text> package has "
				f"an invalid value at runtime: {IN_BULLETS!r}"
			)

		out_bullets = cls.__cleanup_bullets_attr_to_str(out_bullets) if out_bullets else None
		if not out_bullets:
			out_bullets = None
		if not (
			out_bullets is None or (
				isinstance(out_bullets, str) and out_bullets
				and not any(x in out_bullets for x in ' \t\n\r')
			)
		):
			raise ValueError(
				f"Internal error - unexpected value for out_bullets: {out_bullets!r}"
			)

		tab_size = max(int(tab_size), 1)

		return cls(
			indent_empty_lines=indent_empty_lines,
			minimize_indents=minimize_indents,
			list_with_indent=list_with_indent,
			list_no_indent=list_no_indent,
			tab_size=tab_size,
			in_bullets=in_bullets,
			out_bullets=out_bullets,
		)

	@classmethod
	def from_instance(cls: _t.Type[T], instance: 'DocstringToText') -> T:
		return cls.clean_key(
			indent_empty_lines=instance.indent_empty_lines,
			minimize_indents=instance.minimize_indents,
			list_with_indent=instance.list_with_indent,
			list_no_indent=instance.list_no_indent,
			tab_size=instance.tab_size,
			in_bullets=instance.in_bullets,
			out_bullets=instance.out_bullets,
		)


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
		actually private member at class level of a dataclass.
		"""
		__pool_deque: _t.Deque['DocstringToText'] = _deque(maxlen=127)
		__pool_dict: _t.Dict[_ArgsKey, 'DocstringToText'] = dict()
		__pool_reverse: _t.Dict['DocstringToText', _ArgsKey] = dict()

		def __init__(self, *args, **kwargs):
			cls_nm = self.__class__.__qualname__
			raise NotImplementedError(f"{cls_nm} class is static!")

		@classmethod
		def get(cls, key: _ArgsKey) -> _O['DocstringToText']:
			return cls.__pool_dict.get(key, None)

		@classmethod
		def __sync_internal_collections(cls) -> None:
			"""Synchronize internal collections in case they somehow lost their sync."""
			pool = cls.__pool_dict
			pool_deque = cls.__pool_deque
			pool_reverse = cls.__pool_reverse

			# Remember items which existed in the reversed dict, but not in the main pool-dict:
			old_extra_items_reversed = {v: k for v, k in pool_reverse.items() if k not in pool}
			old_extra_items = {k: v for v, k in old_extra_items_reversed.items()}

			# Rebuild the reversed dict:
			cls.__pool_reverse = pool_reverse = {v: k for k, v in pool.items()}

			# Now, ensure that all the instances from deque exist in the dicts:
			deque_items_to_update: _t.Dict[int, DocstringToText] = dict()
			for i, instance in enumerate(pool_deque):
				if instance in pool_reverse:
					continue

				if instance in old_extra_items_reversed:
					# We've lost track of the instance in main pool, but it was in the reversed one before refresh.
					# Let's re-add it:
					key = old_extra_items_reversed[instance]
					# If the key already exists in the pool, then there's another instance there with the same key,
					# but before the refresh deque+reversed had the same one, so use it as the vote of two.
					# If the key isn't there, then the instance was missing in the main pool.
					# Either way, we need to update the both dicts with the old instance (from deque and pre-refresh reverse-pool):
					pool[key] = instance
					pool_reverse[instance] = key
					continue

				# No such instance in the dicts. Let's try to find another one with the same key:
				key = _ArgsKey.from_instance(instance)
				if key in pool:
					# Such instance exists. We need to update it in the deque:
					deque_items_to_update[i] = pool[key]
					continue
				if key in old_extra_items:
					# Old reversed pool contained a (probably different) item with this key. Use it instead:
					old_instance = old_extra_items[key]
					pool[key] = old_instance
					pool_reverse[old_instance] = key
					deque_items_to_update[i] = old_instance
					continue

				# Add the missing item to pools:
				pool[key] = instance
				pool_reverse[instance] = key

			for i, instance in deque_items_to_update.items():
				pool_deque[i] = instance

		@classmethod
		def popleft(cls) -> 'DocstringToText':
			popped = cls.__pool_deque.popleft()
			if popped not in cls.__pool_reverse:
				cls.__sync_internal_collections()

			if popped in cls.__pool_reverse:
				key = cls.__pool_reverse.pop(popped)
			else:
				key = _ArgsKey.from_instance(popped)

			if key in cls.__pool_dict:
				cls.__pool_dict.pop(key)

			return popped

		@classmethod
		def limit(cls) -> int:
			limit = cls.__pool_deque.maxlen
			if limit is None:
				cls.set_limit(127)
				return cls.__pool_deque.maxlen
			if limit < 1:
				cls.set_limit(1)
				return cls.__pool_deque.maxlen
			return limit

		@classmethod
		def set_limit(cls, new_limit: int = 127) -> None:
			cls.__sync_internal_collections()

			new_limit = max(int(new_limit), 1)
			cur_limit = cls.__pool_deque.maxlen
			if cur_limit is not None and new_limit == cur_limit:
				return

			n_to_pop = max(len(cls.__pool_deque) - new_limit, 0)
			for _ in range(n_to_pop):
				cls.popleft()

			n = len(cls.__pool_deque)
			assert n <= new_limit and n == len(cls.__pool_dict) and n == len(cls.__pool_reverse)

			cls.__pool_deque = _deque(cls.__pool_deque, maxlen=new_limit)

			# One more time, just to be sure:
			n = len(cls.__pool_deque)
			pool_reverse = cls.__pool_reverse
			assert n <= new_limit and n == len(cls.__pool_dict) and n == len(pool_reverse) and all(
				x in pool_reverse for x in cls.__pool_deque
			)

		@classmethod
		def append(cls, instance: 'DocstringToText', key: _ArgsKey = None) -> _O['DocstringToText']:
			if key is None:
				key = _ArgsKey.from_instance(instance)
			assert isinstance(key, _ArgsKey), f"Internal error - Not a pool-Key: {key!r}"
			assert isinstance(instance, DocstringToText), f"Internal error - Not a DocstringToText instance: {instance!r}"
			pool = cls.__pool_dict
			assert key not in pool, f"Internal error - attempt to re-add a new instance with the same key to pool: {key!r}"

			limit = cls.limit()
			n = len(cls.__pool_deque)

			if n > limit:
				# This should never happen. But let's try to fix it...
				cls.__sync_internal_collections()
				limit = cls.limit()
				n = len(cls.__pool_deque)
			assert n <= limit

			popped: _O[DocstringToText] = cls.popleft() if n == limit else None

			cls.__pool_deque.append(instance)
			cls.__pool_dict[key] = instance
			cls.__pool_reverse[instance] = key

			return popped

	indent_empty_lines: bool = False
	minimize_indents: bool = True
	list_with_indent: bool = True
	list_no_indent: bool = True
	tab_size: int = TAB_SIZE

	in_bullets: _U[_t.Iterable[str], str] = _field(default=IN_BULLETS)
	out_bullets: _U[_t.Iterable[str], str, None] = _field(default=OUT_BULLETS)

	# Internal "private" fields. Dataclasses with true private fields (dunder attrs)
	# is a real pain to work with. So let's use protected instead:

	_out_bullets_n: int = _field(default=1, init=False, repr=False)
	# Cached func to use for retrieving the output bullet in the final line formatting:
	_out_bullet_get: _O[_C[[ParsedLine, int], str]] = _field(default=None, init=False, repr=False)

	_re_bullet_match: _O[_t_re_match_func] = _field(default=None, init=False, repr=False)

	# Not changed per instance, but still turned to arguments, because
	# slotted argument access is (supposedly) faster than searching a variable in outer scope
	_re_indent_match: _t_re_match_func = _field(default=_re_indent_match_, init=False, repr=False)
	_re_indent_parse: _t_re_match_func = _field(default=_re_indent_parse_, init=False, repr=False)
	_re_number_match: _t_re_match_func = _field(default=_re_number_match_, init=False, repr=False)

	_pass2_change_indents_to_tabs: _C[[_t.List[ParsedLine]], _t.List[ParsedLine]] = _field(
		default=_SpaceToTabsConverter(minimize_indents=True, tab_size=TAB_SIZE).convert,
		init=False, repr=False
	)

	def __new__(
		cls, *_,  # Even for pre-Py3.10, enforce keyword-only args
		# For proper IDE hints, explicit list of identical args:
		indent_empty_lines: bool = False,
		minimize_indents: bool = True,
		list_with_indent: bool = True,
		list_no_indent: bool = True,
		tab_size: int = TAB_SIZE,
		in_bullets: _U[_t.Iterable[str], str] = IN_BULLETS,
		out_bullets: _U[_t.Iterable[str], str, None] = OUT_BULLETS,
	) -> 'DocstringToText':
		"""
		Creates a :class:`DocstringToText` class instance, ensuring
		that only one instance with a given set of parameters exist.

		The same object is returned for subsequent calls with the same
		argument values.
		"""
		args_key = _ArgsKey.clean_key(
			indent_empty_lines=indent_empty_lines,
			minimize_indents=minimize_indents,
			list_with_indent=list_with_indent,
			list_no_indent=list_no_indent,
			tab_size=tab_size,
			in_bullets=in_bullets,
			out_bullets=out_bullets,
		)

		instance = DocstringToText.__InstancePool.get(args_key)
		if instance is not None:
			return instance

		# Create an instance only if it doesn't exist:
		instance = object.__new__(cls)  # Not initialized yet, done later in `__init__` - but with the raw values
		DocstringToText.__InstancePool.append(instance, key=args_key)
		return instance

	def __post_init__(self):
		# Since the dataclass-generated init has no idea about the arg-cleanup we've done in `__new__`,
		# and it simply initialized the instance with all the same raw values,
		# the cleanup needs to be done once again:
		args_key = _ArgsKey.from_instance(self)
		indent_empty_lines, minimize_indents, list_with_indent, list_no_indent, tab_size, in_bullets, out_bullets = args_key

		if out_bullets:
			out_bullets_n = len(out_bullets)
			out_bullet_get_f = self.__out_bullet_get__with_bullet_replacement
		else:
			out_bullets_n = 1
			out_bullet_get_f = self.__out_bullet_get__intact

		re_bullet_match = _re_bullet_match_factory(in_bullets)

		pass2_change_indents_to_tabs_f = self._pass2_change_indents_to_tabs
		if not (minimize_indents and tab_size == TAB_SIZE):
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
	def version() -> _t.Tuple[_t.Union[int, str], ...]:
		"""The module version."""
		return VERSION_TUPLE

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
			return f"{indent_str}{line.number} {line.text}"
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
		text = line.rstrip()
		match = self._re_indent_match(text)
		if not match:
			# Theoretically, '*' qualifier in regex ensures we always match with `_re_indent_match`,
			# but just to be safe...
			return ParsedLine(0, is_empty=True, is_list=False, bullet='', number='', text='')

		indent_str, text = match.groups()
		indent = self.__detect_indent(indent_str)

		match = self._re_bullet_match(text)
		if match:
			# This is the only regex with the second group being optional. So:
			groups = tuple(
				x if x else ''
				for x in match.groups()
			)
			bullet = groups[0]
			text = '' if len(groups) == 1 else groups[1]
			return ParsedLine(indent, is_empty=False, is_list=True, bullet=bullet, number='', text=text)

		match = self._re_number_match(text)
		if match:
			number, text = match.groups()
			return ParsedLine(indent, is_empty=False, is_list=True, bullet='', number=number, text=text)
		if not text:
			# Empty line should have 0 as indent:
			ParsedLine(0, is_empty=True, is_list=False, bullet='', number='', text='')
		return ParsedLine(indent, is_empty=False, is_list=False, bullet='', number='', text=text)

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
