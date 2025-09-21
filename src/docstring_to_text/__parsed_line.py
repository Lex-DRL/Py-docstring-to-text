# encoding: utf-8
"""
Internal :class:`ParsedLine` class - in its own submodule for readability.
"""

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U

from enum import IntEnum as _IntEnum

from .__dataclass import *


class BlockType(_IntEnum):
	"""Block type for stack of indent levels, used during parsing."""
	Indent = 1
	Bullet = 2
	Number = 3


class StackLevelBlock(_t.NamedTuple):
	"""Internal class, used in stack during spaces->tabs conversion.

	Represents hierarchical position of block in stack.

	:ivar indent_spaces_abs: Absolute indent of this block, in spaces, from root.
	:ivar indent_spaces_rel: Relative indent of this block, in spaces, as offset from parent block.
	:ivar indent_tabs_abs: Absolute indent-level of this block, in tabs, from root.
	:ivar list_level:
		When inside a list, indicates the current 0-based list level:
		``-1`` - not in list,
		``0`` - top-level list item,
		``1`` - first indent, etc.
	:ivar in_list:
		The type of list we're currently inside.
		As soon as we enter it, its type preserved until we encounter a different type deeper.
		When not in list, ``BlockType.Indent``.
	:ivar block_type: The type of block.
	:ivar pending_lines:
		Lines at this block level, waiting to be processed,
		after lower-level blocks are done, and we return to this one.
	"""
	indent_spaces_abs: int = 0
	indent_spaces_rel: int = 0
	indent_tabs_abs: int = 0
	list_level: int = -1
	in_list: BlockType = BlockType.Indent
	block_type: BlockType = BlockType.Indent
	pending_lines: _O[_t.List['ParsedLine']] = None

	def copy(self, **overrides) -> 'StackLevelBlock':
		kwargs = dict(
			indent_spaces_abs=self.indent_spaces_abs,
			indent_spaces_rel=self.indent_spaces_rel,
			indent_tabs_abs=self.indent_tabs_abs,
			list_level=self.list_level,
			in_list=self.in_list,
			block_type=self.block_type,
			pending_lines=self.pending_lines,
		)
		overrides = {k: v for k, v in overrides.items() if k in kwargs}
		kwargs.update(overrides)
		return StackLevelBlock(**kwargs)


# class ListStackLevel(_t.NamedTuple):
# 	"""Internal class, used in stack during spaces->tabs conversion.
#
# 	Separate tracking of the **list** block we're currently in
# 	is required for proper bullet selection.
#
# 	:ivar level: Hierarchical level, when inside a list.
# 	:ivar block_type: The type of block.
# 	"""
# 	level: int = 0
# 	block_type: BlockType = BlockType.Bullet


@_dataclass(**_dataclass_slots_args)
class ParsedLine:
	"""A single line parsed into parts the module knows how to deal with.

	:ivar indent: Indent level. Measured in tabs.
	:ivar is_empty:
		Cached flag. ``True`` if the line is empty (all the substrings are ``''``).
	:ivar is_list:
		Cached flag. ``True`` if it's a list item: either ``bullet`` or ``number`` is non-empty.
	:ivar bullet: Starting character(s) of a bulleted list item.
	:ivar number: Number of a numbered list item.
	:ivar number_sep: Separator between ``number`` and ``text`` in numbered list item.
	:ivar text: Actual text of the line. Might be empty even if ``is_list`` is True.
	:ivar list_level:
		For list line, the 0-based level of this item in list hierarchy:
		``-1`` - not in list,
		``0`` - top-level list item,
		``1`` - first indent, etc.
	"""
	indent: int
	is_empty: bool = True
	is_list: bool = False
	list_level: int = -1
	bullet: str = ''
	number: str = ''
	number_sep: str = ''
	text: str = ''

	@classmethod
	def unindent(
		cls,
		lines: _t.Iterable['ParsedLine'], offset: int = 0, clamp_negative: bool = True
	) -> int:
		"""Extract (and remove) the shared indent from the block of lines.

		Mutation of the entire block is done in-place, to prevent unnecessary
		recreation of :class:`ParsedLine` instances and the iterable itself.
		Offset and clamp are applied after unindent. Returned common unindent doesn't account for offset.

		:return: The removed common indent.
		"""
		lines_with_text = [x for x in lines if not x.is_empty]  # empty lines must be ignored
		if not lines_with_text:
			return 0
		common_indent = min(x.indent for x in lines_with_text)
		cls.offset_indent(lines, offset - common_indent)
		if clamp_negative:
			common_indent = max(common_indent, 0)
		return common_indent

	@staticmethod
	def offset_indent(
		lines: _t.Iterable['ParsedLine'], offset: int = 0, clamp_negative: bool = True
	) -> None:
		"""Offset (add/remove) indent for the block of lines.

		Mutation of the entire block is done in-place, to prevent unnecessary
		recreation of :class:`ParsedLine` instances and the iterable itself.
		"""
		if offset == 0 or not lines:
			return
		if clamp_negative:
			for line in lines:
				line.indent = max(line.indent + offset, 0)
			return
		for line in lines:
			line.indent = line.indent + offset

	def block_type(self) -> BlockType:
		"""Classify the line: its block type."""
		if not self.is_list:
			return BlockType.Indent
		if self.bullet:
			return BlockType.Bullet
		assert self.number and self.number_sep
		return BlockType.Number

	def block_id(self):
		"""Classify the line: its full block ID.

		Block ID is a key-tuple, identical for all the lines in the same block.
		"""
		return self.indent, self.is_empty, self.is_list, bool(self.bullet), bool(self.number)
