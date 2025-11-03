# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
"""

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U, Sequence as _S, Iterable as _I

from itertools import chain, zip_longest
from copy import copy
import random

import pytest

from docstring_to_text.__internal_parsed_line import *

from . import parsed_line_utils as _utils
from . import example_data as _data

_t_expected_arg = _U[list, _t.Type[Exception], _t.Tuple[_t.Type[Exception], ...]]


# ==========================================================

# <indent>:
_cases_init_indent: _t.List[_t.Tuple[list, _t_expected_arg]] = []
_cases_init_indent.extend(
	# Errors
	zip_longest(
		_utils.variants_with_filled_defaults(indent=_data.invalid_values_as_int),
		[],
		fillvalue=(TypeError, ValueError)
	),
)
# <indent>: Valid values
_cases_init_indent.extend(
	# From bool
	zip(
		_utils.variants_with_filled_defaults(indent=[False, True]),
		_utils.variants_with_filled_defaults(indent=[0, 1]),
	),
)
_cases_init_indent.extend(
	# Just the same valid values as input and expected:
	zip(
		*_utils.duplicate_seq(
			_utils.variants_with_filled_defaults(indent=list(chain(
				range(-5, 6),
				range(-389 * 9 - 17, 389 * 9 + 1, 389),  # 389 is a random sample step
			))),
			n=2
		),
	),
)

# ----------------------------------------------------------

_cases_init: _t.List[_t.Tuple[list, _t_expected_arg]] = []
_cases_init.extend([
	# Perfectly default:
	(
		# indent, is_empty, is_list, list_level, bullet, number, text
		[0, True, False, -1, '', '', ''],
		[0, True, False, -1, '', '', ''],
	),
])
_cases_init.extend(_cases_init_indent)

# Boolean args - they can never throw an error:
_cases_init.extend(
	# <is_empty>
	zip(
		_utils.variants_with_filled_defaults(is_empty=_data.values_for_str),
		_utils.variants_with_filled_defaults(is_empty=[bool(x) for x in _data.values_for_str]),
	),
)
_cases_init.extend(
	# <is_list>
	zip(
		_utils.variants_with_filled_defaults(is_list=_data.values_for_str),
		_utils.variants_with_filled_defaults(is_list=[bool(x) for x in _data.values_for_str]),
	),
)

# <list_level>:
_cases_init.extend(
	# Errors
	zip_longest(
		_utils.variants_with_filled_defaults(list_level=_data.invalid_values_as_int),
		[],
		fillvalue=(TypeError, ValueError)
	),
)
# <list_level>: Valid values
_cases_init.extend(
	# From bool
	zip(
		_utils.variants_with_filled_defaults(list_level=[False, True]),
		_utils.variants_with_filled_defaults(list_level=[0, 1]),
	),
)
_cases_init.extend(
	# Clamped:
	zip_longest(
		_utils.variants_with_filled_defaults(list_level=list(chain(
			range(-9, 0),
			range(-137 * 13 - 19, -1, 137),  # 137 is a random sample step
		))),
		[],
		fillvalue=next(_utils.variants_with_filled_defaults(list_level=[-1]))
	),
)
_cases_init.extend(
	# Just the same valid values as input and expected:
	zip(
		*_utils.duplicate_seq(
			_utils.variants_with_filled_defaults(list_level=list(chain(
				range(0, 10),
				range(11, 271 * 9 + 12, 271),  # 271 is a random sample step
			))),
			n=2
		),
	),
)

# String args:
_cases_init.extend(
	zip(
		_utils.variants_with_filled_defaults(bullet=_data.values_for_str),
		_utils.variants_with_filled_defaults(bullet=_data.expected_for_str),
	),
)
_cases_init.extend(
	zip(
		_utils.variants_with_filled_defaults(number=_data.values_for_str),
		_utils.variants_with_filled_defaults(number=_data.expected_for_str),
	),
)
_cases_init.extend(
	zip(
		_utils.variants_with_filled_defaults(text=_data.values_for_str),
		_utils.variants_with_filled_defaults(text=_data.expected_for_str),
	),
)


@pytest.mark.parametrize('inputs, expected', _cases_init)
def test_init(inputs: list, expected: _t_expected_arg):
	if _utils.expected_is_error(expected):
		with pytest.raises(expected):
			_utils.from_seq(inputs)
		return

	instance: ParsedLine = _utils.from_seq(inputs)
	instance_tuple = _utils.to_tuple(instance)
	expected_tuple = tuple(expected)
	assert instance_tuple == expected_tuple and all(
		type(x) == type(y)  # The types must match exactly
		for x, y in zip(instance_tuple, expected_tuple)
	)


_valid_expected = list(sorted(set(
	tuple(exp) for inp, exp in _cases_init
	if not _utils.expected_is_error(exp)
)))


@pytest.mark.parametrize('expected', _valid_expected)
def test_copy(expected: tuple):
	instance: ParsedLine = _utils.from_seq(expected)
	cp: ParsedLine = copy(instance)
	assert isinstance(instance, ParsedLine) and isinstance(cp, ParsedLine)
	assert instance == cp and instance is not cp


@pytest.mark.parametrize('expected', _valid_expected)
def test_block_type(expected: tuple):
	instance: ParsedLine = _utils.from_seq(expected)
	assert isinstance(instance, ParsedLine)
	try:
		block_type = instance.block_type()
	except ValueError:
		return
	assert isinstance(block_type, BlockType)


_cases_edit_indent = [
	(
		# Choose many random bulks of lines for each expected value
		random.choices(_valid_expected, k=random.randint(10, 30)),
		off,
		cl
	)
	for _ in range(15)  # For each combination of other args, 15 different line-lists
	for off in (
		random.randint(-1_000, -501),
		random.randint(-500, -300),
		random.randint(-250, -75),
		random.randint(-50, -12),
		-11, -10, -5, -3, -2, -1, 0, 1, 2, 3, 5, 10, 11,
		random.randint(12, 50),
		random.randint(75, 250),
		random.randint(300, 500),
		random.randint(501, 1_000),
	)
	for cl in (True, False)
]


@pytest.mark.parametrize('expected_line_tuples, offset, clamp', _cases_edit_indent)
def test_offset_indent(expected_line_tuples: _t.List[tuple], offset: int, clamp: bool):
	a_lines: _t.List[ParsedLine] = [_utils.from_seq(exp) for exp in expected_line_tuples]
	b_lines: _t.List[ParsedLine] = [copy(x) for x in a_lines]
	assert a_lines == b_lines and all(a is not b for a, b in zip(a_lines, b_lines))

	# Do expected result manually for "B" list:
	for b in b_lines:
		indent: int = 0 if (b.indent is None) else b.indent
		assert isinstance(indent, int)
		indent += offset
		if clamp:
			indent = max(indent, 0)
		b.indent = indent
		assert b.indent == indent

	ParsedLine.offset_indent(a_lines, offset=offset, clamp_negative=clamp)

	pairs = list(zip_longest(a_lines, b_lines))
	for i, (a, b) in enumerate(pairs):
		# i here - just to have the index printed in the message:
		assert i > -1 and a == b and a is not b


@pytest.mark.parametrize('expected_line_tuples, offset, clamp', _cases_edit_indent)
def test_unindent(expected_line_tuples: _t.List[tuple], offset: int, clamp: bool):
	lines: _t.List[ParsedLine] = [_utils.from_seq(exp) for exp in expected_line_tuples]
	lines_with_text = [x for x in lines if not x.is_empty]
	min_indent = min(x.indent for x in lines_with_text) if lines_with_text else 0
	if min_indent == 0:
		ParsedLine.offset_indent(lines, offset=offset, clamp_negative=False)

	ParsedLine.unindent(lines)
	assert min(x.indent for x in lines) == 0
