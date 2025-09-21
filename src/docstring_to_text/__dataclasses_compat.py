# encoding: utf-8
"""
Internal submodule related to cross-version dataclass handling.
"""
__all__ = ('_dataclass', '_field', '_dataclass_slots_args', '_dataclass_slots_and_kw_only_args', )

from dataclasses import dataclass as _dataclass, field as _field

from sys import version_info as __version_info

_dataclass_slots_args = dict() if __version_info < (3, 10) else dict(slots=True)
_dataclass_slots_and_kw_only_args = dict() if __version_info < (3, 10) else dict(slots=True, kw_only=True)
