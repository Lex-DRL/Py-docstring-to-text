# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
"""

from docstring_to_text.__internal_enums import BlockType


def test_block_type():
	all_options = [BlockType.Indent, BlockType.Bullet, BlockType.Number]
	assert tuple(sorted(BlockType)) == tuple(sorted(all_options))
	for x in all_options:
		assert isinstance(x, BlockType) and isinstance(x, int), f"Invalid type: {x!r}"
