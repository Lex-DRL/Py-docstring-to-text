# encoding: utf-8
"""
Internal utility classes related to tracking the stack of blocks we're currently in.
"""

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

__all__ = ('BlockType', 'StackLevel', 'ListStackLevel', )

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U

from collections import deque as _deque
from enum import IntEnum as _IntEnum

from .__dataclass import *


class BlockType(_IntEnum):
	"""Block type for stack of indent levels, used during parsing."""
	Indent = 1
	Bullet = 2
	Number = 3


class IndentLevel(_t.NamedTuple):
	"""A single remembered level of indentation.

	Stored in stack of blocks during parsing.
	"""
	indent: int
	block_type: BlockType


class StackLevel(_t.NamedTuple):
	"""Internal class, used in stack during spaces->tabs conversion.

	:ivar indent_spaces_abs: Absolute indent of this block, in spaces, from root.
	:ivar indent_spaces_rel: Relative indent of this block, in spaces, as offset from parent block.
	:ivar indent_tabs_abs: Absolute indent-level of this block, in tabs, from root.
	:ivar block_type: The type of block.
	"""
	indent_spaces_abs: int
	indent_spaces_rel: int
	indent_tabs_abs: int
	block_type: BlockType = BlockType.Indent


class ListStackLevel(_t.NamedTuple):
	"""Internal class, used in stack during spaces->tabs conversion.

	Separate tracking of the **list** block we're currently in
	is required for proper bullet selection.

	:ivar level: Hierarchical level, when inside a list.
	:ivar block_type: The type of block.
	"""
	level: int = 0
	block_type: BlockType = BlockType.Bullet


_list_block_types = {BlockType.Bullet, BlockType.Number}
_root_level = IndentLevel(0, BlockType.Indent)


@_dataclass(**_dataclass_slots_args)
class BlockStack:
	"""Internal class, used during parsing - to track the whole stack of indentation blocks the active line is in."""
	__active: IndentLevel = _field(default=_root_level, init=False, repr=False)
	__stack: _deque[IndentLevel] = _field(default_factory=_deque, init=False, repr=False)

	# ... and for tracking the list type we're currently in
	__active_list_root: _O[IndentLevel] = _field(default=None, init=False, repr=False)
	__list_roots_stack: _deque[IndentLevel] = _field(default_factory=_deque, init=False, repr=False)

	def __post_init__(self):
		# Instead of dealing with `None` in `__active`, let's just ALWAYS have SOME active level.
		self.__stack.append(self.__active)
		assert (
			len(self.__stack) == 1
			and isinstance(self.__active, IndentLevel)
			and self.__active is self.__stack[0]
			and self.__active is _root_level
			and self.__active_list_root is None
			and isinstance(self.__list_roots_stack, _deque) and not self.__list_roots_stack
		), "Internal error: invalid initial BlockStack state"

	@property
	def active(self) -> IndentLevel:
		"""Active indent level in stack."""
		return self.__active

	@property
	def active_list_root(self) -> _O[IndentLevel]:
		"""The root of the deepest list we're currently in.

		The stack is remembered.
		So, if we were in bullet->numbered->bullet, and we exit the last tone,
		but still are in the numbered one, the numbered becomes active.

		If it's a valid :class:`IndentLevel`, it's also guaranteed to be
		in the main stack.

		``None`` if we're currently not in any type of list.
		"""
		return self.__active_list_root

	def __stack_append(self, level: IndentLevel):
		"""Assuming the given level is already new lowest one in the stack, append it."""
		if level == _root_level:
			level = _root_level  # To have literally the same instance
		self.__stack.append(level)
		self.__active = level
		block_type = level.block_type
		active_list_root = self.__active_list_root
		if block_type in _list_block_types and (active_list_root is None or active_list_root.block_type != block_type):
			self.__list_roots_stack.append(level)
			self.__active_list_root = level

	def set_to(self, new_block_level: IndentLevel):
		"""Switch to the given indent level."""
		stack = self.__stack
		assert stack, "Stack could NEVER get empty"

		stack_pop = self.pop

		new_indent = new_block_level.indent
		for _level in list(reversed(stack)):
			if new_indent > _level.indent:
				# We're simply going a level deeper
				self.__stack_append(new_block_level)
				return
			if new_indent == _level.indent:
				# We're at the same level
				if new_block_level != _level:
					# ... but the block type is different - the new one replaces the old one
					stack_pop()
					self.__stack_append(new_block_level)
				return

			# We unfold in stack
			stack_pop()

		# We've removed all the stack levels.
		assert not(self.__stack or self.__list_roots_stack or self.__active_list_root), (
			"All the stacks must be empty at this point"
		)
		# The new level becomes the root.
		self.__stack_append(new_block_level)

	def pop(self) -> IndentLevel:
		"""Pop one indent level from stack.

		The stack never gets truly empty. When popping while already
		at root level, it stays as the only indent in the stack.
		"""
		active = self.__active
		stack = self.__stack
		lists_stack = self.__list_roots_stack
		assert bool(stack)

		if active == _root_level:
			# We're already at root level.
			# To avoid errors, let's return the "pop", but don't actually pop anything
			assert (
				len(stack) == 1 and stack[0] is active and active is _root_level
				and self.__active_list_root is None
				and not lists_stack
			), "Internal error: invalid stack-at-root state"
			return active

		popped = stack.pop()
		if not stack:
			# We're returning to the root level.
			# Before calling `__stack_append`, we need to reset list-related attribs:
			lists_stack.clear()
			self.__active_list_root = None
			self.__stack_append(_root_level)
			return popped

		# The popped level still left some indents in the stack.
		# Update everything according to the last stack item.
		self.__active = active = stack[-1]
		if self.__active_list_root is None:
			assert not lists_stack, "Internal error: invalid empty-list-stack state"
			return popped

		# We need to ensure no list levels below the active indent are left:
		lists_stack_pop = lists_stack.pop

		active_indent = active.indent
		for list_root in list(reversed(lists_stack)):
			if list_root.indent == active_indent:
				if list_root.block_type != active.block_type:
					# The remaining indent is at the same level as the active block,
					# but block itself isn't a list. One more list-stack-pop needed.
					lists_stack_pop()
				break
			if list_root.indent < active_indent:
				break
			lists_stack_pop()

		self.__active_list_root = lists_stack[-1] if lists_stack else None
		return popped
