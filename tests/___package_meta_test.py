# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Essential sanity check: verify that the bare minimum of the package is importable at all."""

import typing as _t
from typing import Union as _U

import pytest


def test_import_package():
	try:
		import docstring_to_text
	except ImportError as e:
		assert False, f"Can't import the package: {e!r}"
	assert True


def test_import_version():
	try:
		from docstring_to_text import VERSION
	except ImportError as e:
		assert False, f"Can't import the package version: {e!r}"
	assert isinstance(VERSION, str)


def test_import_version_tuple():
	try:
		from docstring_to_text import VERSION_TUPLE
	except ImportError as e:
		assert False, f"Can't import version-tuple of the package: {e!r}"
	assert isinstance(VERSION_TUPLE, tuple) and VERSION_TUPLE
	for seg in VERSION_TUPLE:
		assert (isinstance(seg, str) and seg) or (isinstance(seg, int) and seg > -1), (
			f"Invalid segment in {VERSION_TUPLE!r} version-tuple: {seg!r}"
		)


@pytest.mark.parametrize(
	'ver_str, ver_tuple',
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
	try:
		from docstring_to_text.___package_meta import _version_parts_gen
	except ImportError as e:
		assert False, f"Can't import <_version_parts_gen()>: {e!r}"
	assert tuple(_version_parts_gen(ver_str)) == ver_tuple
