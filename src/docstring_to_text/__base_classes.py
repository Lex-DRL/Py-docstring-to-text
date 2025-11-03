# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Shared base classes and class decorators."""

__all__ = ('T', '_CopyableWithOverrides', '_CopyableWithOverridesProtocol', '_copyable_with_overrides')

import typing as _t

try:
	from typing import Protocol as _Protocol
except ImportError:
	from typing_extensions import Protocol as _Protocol

from abc import ABCMeta as _ABCMeta, abstractmethod as _abstractmethod


T = _t.TypeVar('T')


class _CopyableWithOverrides(metaclass=_ABCMeta):
	"""Defines ``copy`` method + makes the class compatible with :mod:`copy` module."""

	@_abstractmethod
	def _all_args_dict(self) -> dict:
		"""Return a dictionary of all arguments passed to :meth:`__init__` in order to make the copy."""
		raise NotImplementedError

	def copy(self: T, **overrides) -> T:
		"""Create an instance copy with optional field overrides."""
		kwargs = self._all_args_dict()
		overrides = {k: v for k, v in overrides.items() if k in kwargs}
		kwargs.update(overrides)
		cls: _t.Type[T] = type(self)
		return cls(**kwargs)

	def __copy__(self: T) -> T:
		"""Support for :func:`copy.copy`."""
		return self.copy()


# class _CopyableSourceProtocol(_Protocol):
# 	"""Protocol for a class the decorator is applied to."""
# 	def _all_args_dict(self) -> dict: ...


# Since `Type[A & B]` isn't supported in older python (pre-3.10),
# we have to fall back to `_CopyableWithOverridesProtocol[T]` + a specialized `T`:
# _T_CopyableSourceClass = _t.TypeVar('_T_CopyableSourceClass', bound=_CopyableSourceProtocol)


# class _CopyableWithOverridesProtocol(_Protocol[_T_CopyableSourceClass]):
# 	"""Protocol for the final decorated class."""
# 	def copy(self: _T_CopyableSourceClass, **overrides) -> _T_CopyableSourceClass: ...
# 	def __copy__(self: _T_CopyableSourceClass) -> _T_CopyableSourceClass: ...


class _CopyableWithOverridesProtocol(_Protocol):
	"""Protocol for the final decorated class."""
	def copy(self: T, **overrides) -> T: ...
	def __copy__(self: T) -> T: ...


# def _copyable_with_overrides(
# 	cls: _t.Type[_T_CopyableSourceClass]
# ) -> _t.Type[_CopyableWithOverridesProtocol[_T_CopyableSourceClass]]:
# def _copyable_with_overrides(
# 	cls  # type: _t.Type[T & _CopyableSourceProtocol]
# ):
def _copyable_with_overrides(cls: _t.Type[T]) -> _t.Union[_t.Type[T], _t.Type[_CopyableWithOverridesProtocol]]:
	"""A class decorator, doing the same as inheritance from :class:`_CopyableWithOverrides`.

	Should be used whenever there are inheritance issues, such as with :class:`typing.NamedTuple`.
	"""
	try:
		method = cls.copy  # raises `AttributeError` if no such method
		if not callable(method):
			raise AttributeError
		needs_copy = False
	except AttributeError:
		needs_copy = True

	if needs_copy:
		# noinspection PyUnresolvedReferences
		method = cls._all_args_dict  # Source class must have this method, `AttributeError` raised otherwise
		if not callable(method):
			raise AttributeError(f"{cls!r} has '_all_args_dict' attribute, but it's not a callable method: {method!r}")
		cls.copy = _CopyableWithOverrides.copy

	cls.__copy__ = _CopyableWithOverrides.__copy__
	# return cls  # type: _t.Type[T & _CopyableWithOverridesProtocol]
	return cls
