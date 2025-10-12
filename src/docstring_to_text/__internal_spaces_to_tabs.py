# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Internal :class:`SpaceToTabsConverter` class + its accompanying classes.
"""

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U

from .__dataclasses_compat import *
from .__defaults import *
from .__internal_parsed_line import *


_t_lines_chunk = _t.List[_t.Tuple[BlockType, ParsedLine]]  # Pre-classified


class _StackLevelBlock(_t.NamedTuple):
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
	pending_lines: _O[_t_lines_chunk] = None

	def copy(self, **overrides) -> '_StackLevelBlock':
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
		return _StackLevelBlock(**kwargs)


class _FirstExtractedSubBlock(_t.NamedTuple):
	"""Big step in the stack-walking loop: the next chunk to process extracted from the block.

	:ivar common_indent:
		Overall indent (in spaces) of the whole passed block.
		When non-zero, indent not removed, and the whole block is returned as first chunk (``pending`` is empty).
	:ivar extracted_is_final:
		Is the extracted chunk final (``True``) or should be scheduled for next iteration as deeper stack-level (`False``).
	:ivar block_type:
		The type of the "primary" line: the first non-empty line with minimal indent.
		In the edge case where extracted first chunk is an indent over the pending chunk,
		this line is the first one in the pending chunk (it's necessary to know it
		for proper list hierarchies, when list starts with higher-level items).
		Otherwise, this line is somewhere inside the extracted block.
	:ivar extracted: First extracted chunk.
	:ivar pending: Remaining lines. Should be appended as parent stack level to return to later.
	"""
	common_indent: int
	extracted_is_final: bool
	block_type: BlockType
	extracted: _U[_t_lines_chunk, _t.Tuple[()]] = tuple()
	pending: _U[_t_lines_chunk, _t.Tuple[()]] = tuple()

	@staticmethod
	def __detect_first_line_with_min_indent(pending_lines: _t_lines_chunk) -> _t.Tuple[_O[int], _O[int]]:
		"""In the given block, detect the indent and index of the first NON-empty line with minimal indent.

		Both are none in case of an empty list or list with all the empty lines.
		"""
		min_indent: _O[int] = None
		line_index: _O[int] = None
		for i, (l_type, line) in enumerate(pending_lines):
			if line.is_empty:
				continue
			line_indent = line.indent
			if min_indent is None or line_indent < min_indent:
				min_indent = line_indent
				line_index = i
		return min_indent, line_index

	@classmethod
	def extract_from_pending_block(
		cls, pending_lines: _t_lines_chunk
	) -> '_FirstExtractedSubBlock':
		"""Big step in the stack-walking loop: extract the next chunk to process from the block.

		Assuming the given pending block is:
			1. already un-indented
			2. non-empty
			3. isn't just a bunch of empty and zero-indent text lines
		... split it into two parts:
			- The first distinct chunk.
			- The rest of the lines, still unclassified (pending).

		The distinct chunk is one of:
			- A sub-block with shared indent; indent itself is returned as the first value, in spaces.
				- It needs to be appended to the stack and re-entered on the next iteration.
				- Contains all the lines from the start to first non-indented one.
			- An actually extracted uniform block at zero-indent (of the same type), ready to be flushed to output.
			- Both cases might contain (and even start with) empty lines.
		"""
		if not pending_lines:
			# Hierarchy end - empty chunk:
			return _FirstExtractedSubBlock(0, True, BlockType.Indent)

		min_indent, first_real_line_with_min_indent_i = cls.__detect_first_line_with_min_indent(pending_lines)

		if min_indent is None:
			# Hierarchy end - the whole block is only empty lines:
			return _FirstExtractedSubBlock(0, True, BlockType.Indent, extracted=pending_lines)
		assert isinstance(min_indent, int) and isinstance(first_real_line_with_min_indent_i, int)

		first_real_line_type: BlockType = pending_lines[first_real_line_with_min_indent_i][0]

		if min_indent != 0:
			# The "extracted sub-indent" case:
			return _FirstExtractedSubBlock(min_indent, False, first_real_line_type, extracted=pending_lines)

		if first_real_line_with_min_indent_i > 0:
			# Possible split - some extra lines are there before the first unindented one.
			first_chunk: _t_lines_chunk = pending_lines[:first_real_line_with_min_indent_i]
			# But we might start from non-first line simply because there were some empty ones in the beginning.
			# So, check for it:
			if not all(l.is_empty for l_tp, l in first_chunk):
				# Indeed, the extracted chunk has sub-indent:
				return _FirstExtractedSubBlock(
					0, False, first_real_line_type,
					extracted=first_chunk,
					pending=pending_lines[first_real_line_with_min_indent_i:]
				)

		# The general case: starting from the first line, we need to extract the block
		# with the same type and zero-indent.

		first_chunk: _t_lines_chunk = []
		first_chunk_append = first_chunk.append
		remaining_lines: _t_lines_chunk = []

		lines_iter = iter(pending_lines)
		for line_tuple in lines_iter:
			line_type, line = line_tuple
			if line.is_empty or (line.indent == 0 and line_type == first_real_line_type):
				first_chunk_append(line_tuple)
				continue
			remaining_lines.append(line_tuple)
			remaining_lines.extend(lines_iter)
			break

		return _FirstExtractedSubBlock(0, True, first_real_line_type, extracted=first_chunk, pending=remaining_lines)

	# /_FirstExtractedSubBlock


# ==========================================================


def _binary_indent(indent_spaces: int) -> int:
	"""Reduce any indent to 1 or 0. Negative values clamped to 0."""
	return 1 if indent_spaces > 0 else 0


@_dataclass(frozen=True, **_dataclass_slots_args)
class SpaceToTabsConverter:
	"""A separate class for a single most complex step in docstring->text conversion:
	walking the whole text hierarchy and replacing space-indents to tabs.
	"""

	minimize_indents: bool = True
	tab_size: int = TAB_SIZE

	_common_block_spaces_to_tabs: _C[[int], int] = _field(default=_binary_indent, init=False, repr=False)

	def __post_init__(self):
		# Ensure the passed args are the immutable objects of exactly the built-in types:
		minimize_indents = bool(self.minimize_indents)
		tab_size = max(int(self.tab_size), 1)

		common_block_spaces_to_tabs_f: _C[[int], int] = (
			_binary_indent if minimize_indents else self.__common_block_spaces_to_tabs__round_full_tabs
		)

		for name, value in [
			('minimize_indents', minimize_indents),
			('tab_size', tab_size),
			('_common_block_spaces_to_tabs', common_block_spaces_to_tabs_f),
		]:
			# Well-known workaround to re-initialize attributes on frozen instance:
			object.__setattr__(self, name, value)

	def __common_block_spaces_to_tabs__round_full_tabs(self, indent_spaces: int) -> int:
		"""Converts the common space-indents of a block to tabs, when :attr:`minimize_indents` is ``False``.

		Might be assigned to :attr:`_common_block_spaces_to_tabs`.
		"""
		if indent_spaces < 1:
			return 0
		tabs_f = float(indent_spaces) / self.tab_size
		return max(int(tabs_f + 0.4999), 1)

	@staticmethod
	def __detect_sub_block_list_level(
		parent_block: _StackLevelBlock, child_type: BlockType, child_indent: int
	) -> _t.Tuple[int, BlockType]:
		parent_type = parent_block.in_list
		if child_type not in (BlockType.Indent, parent_type):
			# Regardless of indent, we change the list type - so, reset level:
			return 0, child_type

		# The same type as parent
		assert child_indent > -1, "Negative list indents are not allowed"
		if parent_type == BlockType.Indent:
			# Whatever tab-indent level we are in, we aren't in any list yet
			assert child_type == BlockType.Indent, "List-type-change should be covered by the previous condition"
			return -1, BlockType.Indent

		# We're in list, and doing indent of the same list type
		assert parent_type in {BlockType.Bullet, BlockType.Number} and child_type in (BlockType.Indent, parent_type)
		return parent_block.list_level + child_indent, parent_type

	def convert(self, input_lines: _t.List[ParsedLine]) -> _t.List[ParsedLine]:
		"""Second pass on list of :class:`ParsedLine`:

		Turn initial space-indents into proper tabs: that's what :attr:`ParsedLine.indent`
		means now. Again, the :class:`ParsedLine` instances are mutated in-place, but the
		returned list itself is new.

		Prerequisites:
			- first pass: all the items are already joined into paragraph blocks;
			- *(expected first pass output)* the indents in input list are measured **IN SPACES**.
		"""
		output: _t.List[ParsedLine] = []
		pending_stack: _t.List[_StackLevelBlock] = [
			_StackLevelBlock(pending_lines=[
				(x.block_type(), x) for x in input_lines
			])
		]

		# Local-scope vars to get rid of 'dot' operator in the loop:
		output_extend = output.extend
		pending_stack_append = pending_stack.append
		pending_stack_pop = pending_stack.pop
		common_spaces_to_tabs = self._common_block_spaces_to_tabs
		extract_first_sub_block = _FirstExtractedSubBlock.extract_from_pending_block
		detect_sub_block_list_level = self.__detect_sub_block_list_level
		offset_indent = ParsedLine.offset_indent

		def flush_to_output(lines_list: _t.List[ParsedLine], _tab_indent, _list_level):
			for line in lines_list:
				line.indent = _tab_indent
				line.list_level = _list_level
			output_extend(lines_list)

		while pending_stack:
			active_block: _StackLevelBlock = pending_stack_pop()
			pending_lines: _t_lines_chunk = active_block.pending_lines
			if not pending_lines:
				continue

			split: _FirstExtractedSubBlock = extract_first_sub_block(pending_lines)

			if split.extracted_is_final:
				assert split.common_indent == 0 and not split.pending, f"Internal error - invalid extracted block: {split}"
				flush_to_output(
					[x[1] for x in split.extracted],
					active_block.indent_tabs_abs,
					active_block.list_level
				)

				pending_lines = split.pending
				if pending_lines:
					block_type = split.block_type
					list_level, in_list = detect_sub_block_list_level(active_block, block_type, 0)
					pending_stack_append(
						active_block.copy(
							list_level=list_level,
							in_list=in_list,
							block_type=block_type,
							pending_lines=pending_lines
						)
					)
				continue

			# The extracted part isn't final
			extracted = split.extracted
			assert isinstance(extracted, list) and extracted

			if split.common_indent != 0:
				# ... because sub-indent is detected
				assert (
					split.extracted_is_final is False
					and not split.pending and extracted
					and len(extracted) == len(active_block.pending_lines)
				), (
					f"Internal error - invalid indented-only block: {split}"
				)
				common_indent_spaces = split.common_indent
				block_type = split.block_type

				# Warning! In-place line mutation... but thanks to the stack design
				# + pop() at the very first step, each line always belongs to a
				# single stack-block only.
				offset_indent((x[1] for x in extracted), -common_indent_spaces)

				local_tab_offset = common_spaces_to_tabs(common_indent_spaces)
				list_level, in_list = detect_sub_block_list_level(active_block, block_type, local_tab_offset)
				pending_stack_append(
					_StackLevelBlock(
						indent_spaces_abs=active_block.indent_spaces_abs + common_indent_spaces,
						indent_spaces_rel=common_indent_spaces,
						indent_tabs_abs=active_block.indent_tabs_abs + local_tab_offset,
						list_level=list_level,
						in_list=in_list,
						block_type=block_type,
						pending_lines=extracted,
					)
				)
				continue

			# Not final, no indent - the only way we can get here is in the edge case
			# with the extracted chunk having sub-indent + pending, which starts
			# with a zero-indent line

			pending_lines = split.pending
			assert isinstance(pending_lines, list) and pending_lines

			# First, re-schedule the (new) pending block (without the extracted block):
			block_type, first_pending_line = pending_lines[0]
			assert first_pending_line.indent == 0 and not first_pending_line.is_empty
			list_level, in_list = detect_sub_block_list_level(active_block, block_type, 0)
			pending_parent_block = active_block.copy(
				list_level=list_level,
				in_list=in_list,
				block_type=block_type,
				pending_lines=pending_lines
			)
			pending_stack_append(pending_parent_block)

			# Now, schedule the extracted part - to be un-indented on the next step
			list_level, in_list = detect_sub_block_list_level(pending_parent_block, BlockType.Indent, 0)
			sub_indented_first_block = active_block.copy(
				list_level=list_level,
				in_list=in_list,
				block_type=BlockType.Indent,
				pending_lines=extracted
			)
			pending_stack_append(sub_indented_first_block)

		return output

	# /SpaceToTabsConverter
