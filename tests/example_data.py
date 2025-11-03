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

from docstring_to_text.__base_classes import T


class DummyClass:
	pass


def dummy_func(*args, **kwargs):
	return None

def dummy_func_empty():
	return None

def dummy_func_with_arg(arg: T) -> T:
	return arg

def dummy_func_with_kwargs(aaa: int = 0, bbb: str = ''):
	return None

def dummy_func_with_arg_and_kwargs(arg: T, aaa: int = 0, bbb: str = '') -> T:
	return arg


invalid_values_as_int: list = [
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
	dummy_func,  # a function with no required arguments
	dummy_func_empty,  # a function with no args
	dummy_func_with_arg,  # a function with positional args
	dummy_func_with_kwargs,  # a function with kw-args
	dummy_func_with_arg_and_kwargs,  # a function with args + kw-args
]

values_for_str: list = list(chain(
	invalid_values_as_int,
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

expected_for_str = [str(x) if x else '' for x in values_for_str]
