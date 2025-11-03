# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
"""

from enum import IntEnum as _IntEnum


class BlockType(_IntEnum):
	"""Block type enum for stack of indent levels, used during parsing."""
	Indent = 1
	Bullet = 2
	Number = 3
