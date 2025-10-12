# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
"""

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U, Sequence as _S, Iterable as _I

from itertools import chain, zip_longest

import pytest

from docstring_to_text.__internal_parsed_line import *


def test_block_type():
	all_options = [BlockType.Indent, BlockType.Bullet, BlockType.Number]
	assert tuple(sorted(BlockType)) == tuple(sorted(all_options))
	for x in all_options:
		assert isinstance(x, BlockType) and isinstance(x, int), f"Invalid type: {x!r}"


# ==========================================================


class DummyClass:
	pass


def _from_seq(args: _S) -> ParsedLine:
	indent, is_empty, is_list, list_level, bullet, number, text = args
	return ParsedLine(
		indent=indent, is_empty=is_empty, is_list=is_list, list_level=list_level, bullet=bullet, number=number, text=text
	)


def _to_tuple(instance: ParsedLine) -> tuple:
	return (
		instance.indent, instance.is_empty, instance.is_list, instance.list_level,
		instance.bullet, instance.number, instance.text,
	)


def _all_arg_names_in_order() -> _t.Tuple[str, ...]:
	return 'indent', 'is_empty', 'is_list', 'list_level', 'bullet', 'number', 'text'


def _variants_with_filled_defaults(
	indent: _S = (),
	is_empty: _S = (),
	is_list: _S = (),
	list_level: _S = (),
	bullet: _S = (),
	number: _S = (),
	text: _S = (),
	def_indent = 0,
	def_is_empty = True,
	def_is_list = False,
	def_list_level = -1,
	def_bullet = '',
	def_number = '',
	def_text = '',
) -> _t.Generator[list, _A, None]:
	"""
	Generator, building a bunch of test-case-values (as lists) with:

	- only one argument changing between cases,
	- and the rest of arguments filled with defaults.
	"""
	arg_names_in_order = _all_arg_names_in_order()
	overrides_in_order = (indent, is_empty, is_list, list_level, bullet, number, text)
	defaults_in_order = (def_indent, def_is_empty, def_is_list, def_list_level, def_bullet, def_number, def_text)
	all_args_dict: _t.Dict[str, _t.Tuple[_S, _A]] = {
		k: (overrides, default)
		for k, overrides, default in zip(
			arg_names_in_order, overrides_in_order, defaults_in_order
		)
	}
	non_defaults = {
		k: overrides
		for k, (overrides, default) in all_args_dict.items()
		if overrides
	}
	if not non_defaults:
		raise RuntimeError(f"Invalid test - No arg specified for a set of values")
	if len(non_defaults) != 1:
		raise RuntimeError(f"Invalid test - Only one arg can have non-default value. Got: {non_defaults!r}")

	options_arg, option_values = next(iter(non_defaults.items()))
	kwargs = {
		k: default
		for k, (overrides, default) in all_args_dict.items()
		if not overrides
	}
	for value in option_values:
		# We can safely reuse the same dict by always changing the same key:
		kwargs[options_arg] = value
		yield [
			kwargs[k] for k in arg_names_in_order
		]


def _duplicate_seq(items: _I, n: int = 2, out_type: _t.Type[_S] = list) -> _t.Tuple[_S, ...]:
	items_concrete = tuple(items)
	return tuple(out_type(items_concrete) for _ in range(n))


# ==========================================================


_invalid_values_as_int = [
	None,
	[], [0], ['0'], [1.0, 2, '3.17'],
	(), (0, ), ('1', ),
	dict(), {0: 0}, {7: '13'}, {'7': 13},
	set(), {0, }, {'99', },
	'', 'None', 'a', '_0', '_00', '_1', '1.0',
	int,  # type, not value
	object, type, tuple, list, str, iter, range,
	range(0), range(5), iter(range(0)), iter(range(5)), (x * 2 for x in range(5)),  # iterator/generator
	DummyClass,
	_t, pytest,
	test_block_type,  # a function with no arguments
	_from_seq,  # a function with positional args
	_variants_with_filled_defaults,  # a function with kw-args
]

_values_for_str = list(chain(
	_invalid_values_as_int,
	[
		False, True,
		'text', 'qqq', '- asdf', '* qwer',
		' ', '\n', '\t', '  \t  ', '\t  \t',
		'•○■►★', '•○■►★ \t•○■►★',
		'~Lorem ipsum dolor sit amet!', 'А что если по-русски?',
		':', '~~', '`', '"', "'",
		"Let's go!!!",
	]
))
_expected_for_str = [str(x) if x else '' for x in _values_for_str]


@pytest.mark.parametrize('inputs, expected', list(chain(
	[
		# Perfectly default:
		(
			# indent, is_empty, is_list, list_level, bullet, number, text
			[0, True, False, -1, '', '', ''],
			[0, True, False, -1, '', '', ''],
		),
	],

	# Errors for <indent>:
	zip_longest(
		_variants_with_filled_defaults(indent=_invalid_values_as_int),
		[],
		fillvalue=(TypeError, ValueError)
	),
	# Valid values for <indent>:
	zip(
		_variants_with_filled_defaults(indent=[False, True]),
		_variants_with_filled_defaults(indent=[0, 1]),
	),
	zip(
		*_duplicate_seq(  # Just the same values as input and expected:
			_variants_with_filled_defaults(indent=list(chain(
				range(-5, 6),
				range(-389*9 - 17, 389*9 + 1, 389), # 389 is a random sample step
			))),
			n=2
		),
	),

	# Boolean args - they can never throw an error:
	zip(
		_variants_with_filled_defaults(is_empty=_values_for_str),
		_variants_with_filled_defaults(is_empty=[bool(x) for x in _values_for_str]),
	),
	zip(
		_variants_with_filled_defaults(is_list=_values_for_str),
		_variants_with_filled_defaults(is_list=[bool(x) for x in _values_for_str]),
	),

	# Errors for <list_level>:
	zip_longest(
		_variants_with_filled_defaults(list_level=_invalid_values_as_int),
		[],
		fillvalue=(TypeError, ValueError)
	),
	# Valid values for <list_level>:
	zip(
		_variants_with_filled_defaults(list_level=[False, True]),
		_variants_with_filled_defaults(list_level=[0, 1]),
	),
	# Clamped:
	zip_longest(
		_variants_with_filled_defaults(list_level=list(chain(
			range(-9, 0),
			range(-137 * 13 - 19, -1, 137),  # 137 is a random sample step
		))),
		[],
		fillvalue=next(_variants_with_filled_defaults(list_level=[-1]))
	),
	zip(
		*_duplicate_seq(
			_variants_with_filled_defaults(list_level=list(chain(
				range(0, 10),
				range(11, 271 * 9 + 12, 271),  # 271 is a random sample step
			))),
			n=2
		),
	),

	# String args:
	zip(
		_variants_with_filled_defaults(bullet=_values_for_str),
		_variants_with_filled_defaults(bullet=_expected_for_str),
	),
	zip(
		_variants_with_filled_defaults(number=_values_for_str),
		_variants_with_filled_defaults(number=_expected_for_str),
	),
	zip(
		_variants_with_filled_defaults(text=_values_for_str),
		_variants_with_filled_defaults(text=_expected_for_str),
	),
)))
def test_init(inputs: list, expected: _U[list, _t.Type[Exception], _t.Tuple[_t.Type[Exception], ...]]):
	is_expected_error = isinstance(expected, type) and issubclass(expected, Exception)
	is_expected_error = is_expected_error or (
		isinstance(expected, tuple) and expected and any(
			isinstance(x, type) and issubclass(x, Exception)
			for x in expected
		)
	)
	if is_expected_error:
		with pytest.raises(expected):
			_from_seq(inputs)
		return

	instance = _from_seq(inputs)
	instance_tuple = _to_tuple(instance)
	expected_tuple = tuple(expected)
	assert instance_tuple == expected_tuple and all(
		type(x) == type(y)  # The types must match exactly
		for x, y in zip(instance_tuple, expected_tuple)
	)
