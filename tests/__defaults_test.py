# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
"""

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U


def _bullets_var_validator(getter_f: _C[[], str], required_chars: str):
	try:
		bullets = getter_f()
	except ImportError as e:
		assert False, repr(e)
		return
	assert isinstance(bullets, str) and bullets
	bullets_set = set(bullets)
	assert all(x in bullets_set for x in required_chars)


def test_in_bullets():
	def getter():
		from docstring_to_text.__defaults import IN_BULLETS
		return IN_BULLETS
	_bullets_var_validator(getter, '-*•○■')


def test_in_bullets_with_long_dashes():
	def getter():
		from docstring_to_text.__defaults import IN_BULLETS_WITH_LONG_DASHES
		return IN_BULLETS_WITH_LONG_DASHES
	_bullets_var_validator(getter, '—–-*•○■')


def test_out_bullets():
	def getter():
		from docstring_to_text.__defaults import OUT_BULLETS
		return OUT_BULLETS
	_bullets_var_validator(getter, '•○■')


def test_tab_size():
	try:
		from docstring_to_text.__defaults import TAB_SIZE
	except ImportError as e:
		assert False, repr(e)
		return
	assert isinstance(TAB_SIZE, int) and TAB_SIZE > 0
