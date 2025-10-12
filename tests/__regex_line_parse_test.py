# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
"""

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U

import pytest

from docstring_to_text.__regex_line_parse import *


def _match_validator(match: _t_re_match_result, groups_list: _O[_t.List[str]], min_groups: int = 0):
	"""Generic regex-match-to-groups tester."""
	if not match:
		assert groups_list is None
		return

	match_groups = [x if x else '' for x in match.groups()]  # To list + no ambiguity: '' for optional (and missing) groups
	while len(match_groups) < min_groups:
		match_groups.append('')
	assert match_groups == groups_list


@pytest.mark.parametrize('line, group_1, group_2', [
	('', '', ''),
	('  ', '  ', ''),
	('\t', '\t', ''),
	('  \t  ', '  \t  ', ''),
	('  \t  - zxc', '  \t  ', '- zxc'),
	('  qqq', '  ', 'qqq'),
	('\t`asd', '\t', '`asd'),
	('  \t  : qwe', '  \t  ', ': qwe'),
	('  \t  | Lorem ipsum! Dolor sit amet...   ', '  \t  ', '| Lorem ipsum! Dolor sit amet...   '),
	('~Lorem ipsum! Dolor sit amet...   \t ', '', '~Lorem ipsum! Dolor sit amet...   \t ')
])
def test__re_indent_match_(line: str, group_1: str, group_2: str):
	_match_validator(_re_indent_match_(line), [group_1, group_2])


@pytest.mark.parametrize('indent, groups', [
	('', ['', '', '']),
	(' ', ['', ' ', '']),
	('   ', ['', '   ', '']),
	('  \t ', ['', '  ', '\t ']),

	('\t', ['\t', '', '']),
	('\t\t\t', ['\t\t\t', '', '']),

	('\t  ', ['\t', '  ', '']),
	('\t\t \t \t\t', ['\t\t', ' ', '\t \t\t']),
	('\t\r\t', ['\t', '\r', '\t']),
	('\t \r \t \r \t ', ['\t', ' \r ', '\t \r \t ']),
	('  \r  \t ', ['', '  \r  ', '\t ']),

	# All these are invalid patterns: they have non-whitespace chars. But still, we expect the following:
	('\t\t\t.:-qqq asdf! ~ \t = !!! ddd', ['\t\t\t', '.:-qqq asdf! ~ ', '\t = !!! ddd']),
	(
		'\t\t\t.:-qqq asdf! ~ \t = !!! ddd \t zzz \r\t aaa \t',
		['\t\t\t', '.:-qqq asdf! ~ ', '\t = !!! ddd \t zzz \r\t aaa \t']
	),
])
def test__re_indent_parse_(indent: str, groups: _t.List[str]):
	_match_validator(_re_indent_parse_(indent), groups)


@pytest.mark.parametrize('line, groups', [
	('', None),
	('1', None),
	('1.', ['1.', '']),
	('1.   ', ['1.', '']),
	('1.   txt', ['1.', 'txt']),
	('123: txt', ['123:', 'txt']),
	('123.\n456.789. \tqqq', ['123.\n456.789.', 'qqq']),  # Input should have *NO* newlines, but still, we catch that
	('123~456`789:qqq', ['123~456`789:', 'qqq']),
	('a.b.c. qqq', ['a.b.c.', 'qqq']),
	('a.b.c.qqq', ['a.b.c.', 'qqq']),
	('a.b.c.qqq.', ['a.b.c.', 'qqq.']),
	('a-b-c)qqq', ['a-b-c)', 'qqq']),
	("a`b'c~d: qqq", ["a`b'c~d:", 'qqq']),

	('aa-bb-cc.qqq', None),  # fail: double letter
	('a-bb-cc.qqq', None),  # fail: wrong end after 'a'
	('a)bb-cc.qqq', ['a)', 'bb-cc.qqq']),
	('1-a,b... qqq', ['1-a,b...', 'qqq']),
])
def test__re_number_match_(line: str, groups: _O[_t.List[str]]):
	_match_validator(_re_number_match_(line), groups)


@pytest.mark.parametrize('invalid_input, error_type', [
	('', ValueError),
	(' ', ValueError),
	('* -', ValueError),
	('*\t-', ValueError),
	('*\n-', ValueError),
	('\t  \t \r \n\t', ValueError),
	('a', ValueError),
	('bcd-efg', ValueError),
	('*bcd-efg_', ValueError),

	(None, TypeError),
	(False, TypeError),
	(True, TypeError),
	(Exception, TypeError),
	(object, TypeError),
	(object(), TypeError),
	(type, TypeError),
	(_t, TypeError),
	(_A, TypeError),
	(callable, TypeError),
	(_t_re_match_func, TypeError),
	(str, TypeError),
	(str(), ValueError),

	(0, TypeError),
	(1, TypeError),
	(456, TypeError),
	(1.234, TypeError),
	(list('abc'), TypeError),
	(tuple('def'), TypeError),
	(set('ghi'), TypeError),
	(dict(), TypeError),
	({'a': 3, 'b': 14, 'c': 16}, TypeError),
])
def test__re_bullet_match_factory_errors(invalid_input, error_type: _t.Type[Exception]):
	with pytest.raises(error_type):
		_re_bullet_match_factory(invalid_input)


@pytest.mark.parametrize('in_bullets, line, groups', [
	('*', '', None),
	('*', ' ', None),
	('*', ' text ', None),
	('*', ' *', None),
	('*', '*', ['*', '']),
	('*', '* ', ['*', '']),
	('*', '* text', ['*', 'text']),
	('*', '*** text', ['***', 'text']),
	('*', '* **text', ['*', '**text']),
	('*', '* ** text', ['*', '** text']),
	('*', '*abcd', None),
	('*', '- ** text', None),
	('*', '- * text', None),
	('*', '• * text', None),

	('-*•○', '', None),
	('-*•○', 'qqq', None),
	('-*•○', 'qwe', None),
	('-*•○', '.: *-qwe', None),
	('-*•○', '*.: -qwe', None),
	('-*•○', '* .: -qwe', ['*', '.: -qwe']),
	('-*•○', '-\t*list item*', ['-', '*list item*']),
	('-*•○', '- \t* list item *', ['-', '* list item *']),
	('-*•○', '*text', None),
	('-*•○', '* text', ['*', 'text']),
	('-*•○', '• text', ['•', 'text']),
	('-*•○', '○ text', ['○', 'text']),
	('-*•○', '- text', ['-', 'text']),
	('-*•○', '** \t text', ['**', 'text']),
	('-*•○', '•• text', ['••', 'text']),
	('-*•○', '○○ text', ['○○', 'text']),
	('-*•○', '-- text', ['--', 'text']),
	('-*•○', '- - text', ['-', '- text']),
	('-*•○', '*-•○ ○ lorem ipsum', ['*-•○', '○ lorem ipsum']),
	('-*•○', '*-•★ ○ lorem ipsum', None),
	('-*•○', '– text', None),
	('-*•○', '— text', None),
	('-*•○', '★ text', None),
])
def test__re_bullet_match_factory(in_bullets: str, line: str, groups: _O[_t.List[str]]):
	try:
		func = _re_bullet_match_factory(in_bullets)
	except Exception as e:
		assert False, f"Error raised for {in_bullets!r} bullets: {e!r}"
		return
	_match_validator(func(line), groups, min_groups=2)
