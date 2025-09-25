# encoding: utf-8

# It should be a hard-coded string, for build tools to detect it:
VERSION = "1.0.2"

import typing as _t


def __version_parts_gen(ver_str: str) -> _t.Generator[_t.Union[int, str], _t.Any, None]:
	for part_by_dot in ver_str.split("."):
		for part in part_by_dot.split('-'):
			if not part:
				continue
			try:
				yield int(part)
			except Exception:
				yield part


# For actual python code to compare:
VERSION_TUPLE: _t.Tuple[_t.Union[int, str], ...] = tuple(__version_parts_gen(VERSION))
