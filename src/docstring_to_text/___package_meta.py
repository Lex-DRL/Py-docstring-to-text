# encoding: utf-8

# It should be a hard-coded string, as close to the beginning of file as possible,
# for Hatchling build tools to properly parse it:
VERSION = "1.0.4-alpha2"


# =============================================================
# Parsing it into a tuple, more suitable for version comparison


import typing as _t

import re as _re

_re_separate = _re.compile(
	# r'^'  # not necessary with `re.match()`
	r'([a-zA-Z_0-9\s]*)'  # valid version-seg characters - greedy
	r'[^a-zA-Z_0-9\s]+'  # anything else
	r'(.*?)'  # the remainder of the string, possibly with a mix of both - lazy
	r'$'  # must match the entire string
).match


def _raw_version_parts_gen(ver_str: str) -> _t.Generator[str, _t.Any, None]:
	"""Splits version string into parts.

	Parts contain only alphanumeric characters, underscores and spaces/tabs.
	Anything else considered a separator.
	Integer sub-parts aren't extracted yet.
	"""
	assert ver_str and isinstance(ver_str, str)
	remainder: str = ver_str.strip()

	match = _re_separate(remainder)
	while match:
		groups = [
			x.strip() if x else ''
			for x in match.groups()
		]
		while len(groups) < 2:
			groups.append('')
		part, remainder = groups[:2]

		# to replace any whitespace sequences to single spaces:
		part = ' '.join(part.split())
		if part:
			yield part

		match = _re_separate(remainder)

	if remainder:
		yield remainder


_re_int_extractor = _re.compile(
	r'([^0-9]*)'
	r'([0-9]+)'
	r'([^0-9].*?)?'
	r'$'
).match


def _part_to_final_segs_gen(str_part: str) -> _t.Generator[_t.Union[int, str], _t.Any, None]:
	"""Given one part, separates it into actual version segments."""
	assert str_part and isinstance(str_part, str)
	remainder: str = str_part

	while remainder:
		remainder = remainder.strip().strip('_')
		match = _re_int_extractor(remainder)
		if not match:
			assert not any(x in remainder for x in '0123456789'), (
				f"Internal error: last version-remainder for {str_part!r} part still contains digits: {remainder!r}"
			)
			break

		groups = [
			x.strip().strip('_') if x else ''
			for x in match.groups()
		]
		while len(groups) < 3:
			groups.append('')
		text_prefix, int_str, remainder = groups[:3]

		if text_prefix:
			yield text_prefix

		yield int(int_str)

	if remainder:
		yield remainder


def _version_parts_gen(ver_str: str) -> _t.Generator[_t.Union[int, str], _t.Any, None]:
	"""Parse version string into parts, with ints.

	- '0.1.2' -> (0, 1, 2)
	- '0.1.2rc' -> (0, 1, 2, 'rc')
	- '0.1.2rc0123' -> (0, 1, 2, 'rc', 123)
	- '0.1.2-alpha1' -> (0, 1, 2, 'alpha', 1)
	- '0-1-2-beta-1' -> (0, 1, 2, 'beta', 1)  # though, non-compliant with semantic versioning
	- '0.1.2.beta.2' -> (0, 1, 2, 'beta', 2)
	"""
	for str_part in _raw_version_parts_gen(ver_str):
		for seg in _part_to_final_segs_gen(str_part):
			yield seg


# For actual python code to compare:
VERSION_TUPLE: _t.Tuple[_t.Union[int, str], ...] = tuple(_version_parts_gen(VERSION))
