# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Internal :class:`ParsedLine` class + its accompanying classes.
Depends only on built-in types (and not on other custom classes in the package).
"""

import typing as _t

from enum import IntEnum as _IntEnum

from .__dataclasses_compat import *


T = _t.TypeVar('T')


class BlockType(_IntEnum):
	"""Block type enum for stack of indent levels, used during parsing."""
	Indent = 1
	Bullet = 2
	Number = 3


@_dataclass(**_dataclass_slots_args)
class ParsedLine:
	"""A single line parsed into segments the module knows how to deal with. Mutable dataclass.

	:ivar indent: Indent level. Measured in tabs.
	:ivar is_empty:
		Cached flag. ``True`` if the line is empty (all the substrings are ``''``).
	:ivar is_list:
		Cached flag. ``True`` if it's a list item: either ``bullet`` or ``number`` is non-empty.
	:ivar bullet: Starting character(s) of a bulleted list item.
	:ivar number: Number of a numbered list item.
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
	text: str = ''

	def __post_init__(self):
		# Enforce explicit types. Not a true validation (done only at init), but better than nothing:
		self.indent = int(self.indent)
		self.is_empty = bool(self.is_empty)
		self.is_list = bool(self.is_list)
		self.list_level = max(int(self.list_level), -1)
		self.bullet = str(self.bullet) if self.bullet else ''
		self.number = str(self.number) if self.number else ''
		self.text = str(self.text) if self.text else ''

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
		assert self.number
		return BlockType.Number

	def block_id(self):
		"""Classify the line: its full block ID.

		Block ID is a key-tuple, identical for all the lines in the same block.
		"""
		return self.indent, self.is_empty, self.is_list, bool(self.bullet), bool(self.number)
