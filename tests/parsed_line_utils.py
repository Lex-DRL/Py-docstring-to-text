# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
"""

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U, Sequence as _S, Iterable as _I

from docstring_to_text.__internal_parsed_line import *


# ==========================================================


def from_seq(args: _S) -> ParsedLine:
	indent, is_empty, is_list, list_level, bullet, number, text = args
	return ParsedLine(
		indent=indent, is_empty=is_empty, is_list=is_list, list_level=list_level, bullet=bullet, number=number, text=text
	)


def to_tuple(instance: ParsedLine) -> tuple:
	return (
		instance.indent, instance.is_empty, instance.is_list, instance.list_level,
		instance.bullet, instance.number, instance.text,
	)


def all_arg_names_in_order() -> _t.Tuple[str, ...]:
	return 'indent', 'is_empty', 'is_list', 'list_level', 'bullet', 'number', 'text'


def variants_with_filled_defaults(
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
	arg_names_in_order = all_arg_names_in_order()
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


def duplicate_seq(items: _I, n: int = 2, out_type: _t.Type[_S] = list) -> _t.Tuple[_S, ...]:
	items_concrete = tuple(items)
	return tuple(out_type(items_concrete) for _ in range(n))


def _is_exception_type(arg: _A) -> bool:
	return isinstance(arg, type) and issubclass(arg, Exception)


def expected_is_error(expected: _A) -> bool:
	if _is_exception_type(expected):
		return True
	if (
		isinstance(expected, tuple) and expected and any(
			_is_exception_type(x) for x in expected
		)
	):
		return True
	return False
