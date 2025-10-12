# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Supporting regexes for the main processor."""

__all__ = (
	'_t_re_match_result', '_t_re_match_func',
	'_re_indent_match_', '_re_indent_parse_', '_re_number_match_',
	'_re_bullet_match_factory',
)

import typing as _t
from typing import Any as _A, Callable as _C, Optional as _O, Union as _U

import re as _re

_t_re_match_result = _O[_re.Match[str]]
_t_re_match_func = _C[[str], _t_re_match_result]

# Given a line with no line breaks, splits the indent and the actual text:
_re_indent_match_: _t_re_match_func = _re.compile(
	r'(\s*)'
	r'(.*?)$'
).match

# Given a pre-extracted indent part (whitespace-only) of a line,
# does a single iteration of extracting its leading tab part.
# Used in overall indent-level detection.
_re_indent_parse_: _t_re_match_func = _re.compile(
	r'(\t*)'
	r'([^\t]*)'
	r'(.*?)$'
).match

# Given a line without leading indent, extracts the numeration,
# if it's a numbered list item:
_re_number_match_: _t_re_match_func = _re.compile(
	r"("  # First group: the numeration
	r"(?:"  # The optional multipart prefix, that might repeat
	r"\s*"  # The passed input string already doesn't have spaces in the beginning, but '1. 2.' / 'a) b)' might have
	r"(?:\d+|[a-zA-Z])"  # The number or a single latin letter
	r"[_'`´,.:)~—–-]+"  # Any kind of immediate separators: '1.', '1)', 'a:', etc.
	r")*" # ... the "might repeat" part (or might be absent)
	r"\s*"    # Still inside the group...
	r"(?:\d+|[a-zA-Z])"  # ... the last part of the number, it's required...
	r"[.:)]+"  # ... and must end with a much more restricted set of separator characters.
	r")\s*"  # First group ends, optional space after.
	r'(.*?)$'  # Second part: the actual text
).match

_re_has_whitespaces: _t_re_match_func = _re.compile(
	r'\s+'
).search

_re_has_alphanumeric: _t_re_match_func = _re.compile(
	r'[a-zA-Z0-9]+'
).search


def _re_bullet_match_factory(in_bullets: str) -> _t_re_match_func:
	"""Builds a regex-match for a specific pre-validated ``in_bullets`` argument."""
	if not isinstance(in_bullets, str):
		raise TypeError(f"Not a string: {in_bullets!r}")
	if not in_bullets:
		raise ValueError(f"Not a set of in-bullet characters: {in_bullets!r}")
	if _re_has_whitespaces(in_bullets):
		raise ValueError(f"A set of in-bullet characters can't contain whitespace: {in_bullets!r}")
	if _re_has_alphanumeric(in_bullets):
		raise ValueError(f"A set of in-bullet characters can't contain numbers or letters: {in_bullets!r}")

	in_bullets_for_re = _re.escape(in_bullets)
	return _re.compile(
		f'([{in_bullets_for_re}]+)'
		r'(?:'
		r'\s+(.*?)'  # Must have at least one space after bullet to prevent matching `\t*bold* text`...
		r'|'
		r'\s*'  # ... or the bullet has to be the only non-whitespace character on the line
		r')$'
	).match
