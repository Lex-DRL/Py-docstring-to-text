# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
"""

import typing as _t
from typing import Union as _U

import pytest

from docstring_to_text.___package_meta import _version_parts_gen

@pytest.mark.parametrize(
	"ver_str, ver_tuple",
	[
		('1.2:3', (1, 2, 3)),
		('4`5 6', (4, 5, 6)),
		('7 8!`-~9--.__Release Candidate__', (7, 8, 9, 'Release Candidate')),
		('0.1.2', (0, 1, 2)),
		('0.1.2rc', (0, 1, 2, 'rc')),
		('0.1.2rc0', (0, 1, 2, 'rc', 0)),
		('0.1.2rc1', (0, 1, 2, 'rc', 1)),
		('0.1.2rc0123', (0, 1, 2, 'rc', 123)),
		('0.1.2-alpha', (0, 1, 2, 'alpha')),
		('0.1.2-alpha1', (0, 1, 2, 'alpha', 1)),
		('0-1-2-beta-1', (0, 1, 2, 'beta', 1)),
		('0.1.2.beta.2', (0, 1, 2, 'beta', 2)),
	]
)
def test__version_parts_gen(ver_str: str, ver_tuple: _t.Tuple[_U[int, str], ...]):
	assert tuple(_version_parts_gen(ver_str)) == ver_tuple
