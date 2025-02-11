"""The extension for the PurePosixPath to support our root."""

from __future__ import annotations

import itertools
import os
import string

import more_itertools
import shv.rpcri


class SHVPath:
    """The SHV path helper.

    This is designed to be close to the pathlib while providing the SHV path
    specific behavior. But some of the methods just doesn't make sense in the
    respect of the SHV path (such as ``is_absolute``).

    We can't easilly use pathlib based version because there are huge
    differences in the implementation (not external API) between Python 3.11
    and 3.12 and later versions.
    """

    def __init__(self, *pathsegments: str | os.PathLike) -> None:
        self._hash: int
        self._parts: list[str] = []
        for segment in itertools.chain.from_iterable(
            os.fspath(pth).split("/") for pth in pathsegments
        ):
            if any(c in segment for c in string.whitespace):
                raise ValueError("SHV path can't contain white space characters")
            if segment == "..":
                if self._parts:
                    self._parts.pop()
            elif segment:
                self._parts.append(segment)

    @staticmethod
    def _parse_parts(*pathsegments: str | os.PathLike | SHVPath) -> list[str]:
        raise NotImplementedError

    @property
    def parts(self) -> tuple[str, ...]:
        """Tuple giving access to the path's various components."""
        return tuple(self._parts)

    def __str__(self) -> str:
        return "/".join(self._parts)

    def __fspath__(self) -> str:
        return str(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self})"

    def __reduce__(self) -> tuple[type[SHVPath], tuple[str, ...]]:
        return self.__class__, tuple(self._parts)

    def __bool__(self) -> bool:
        return bool(self._parts)

    def __truediv__(self, key: str | os.PathLike | SHVPath) -> SHVPath:
        return type(self)(*self._parts, key)

    def __rtruediv__(self, key: str | os.PathLike) -> SHVPath:
        return type(self)(key, *self._parts)

    def __hash__(self) -> int:
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(self._parts)
            return self._hash

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str | os.PathLike):
            return os.fspath(self) == os.fspath(other)
        return super().__eq__(other)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, str | os.PathLike):
            return os.fspath(self) < os.fspath(other)
        return False

    def __le__(self, other: object) -> bool:
        if isinstance(other, str | os.PathLike):
            return os.fspath(self) <= os.fspath(other)
        return False

    def __gt__(self, other: object) -> bool:
        if isinstance(other, str | os.PathLike):
            return os.fspath(self) > os.fspath(other)
        return False

    def __ge__(self, other: object) -> bool:
        if isinstance(other, str | os.PathLike):
            return os.fspath(self) >= os.fspath(other)
        return False

    @property
    def parents(self) -> SHVPath:
        """An immutable sequence providing access to the logical ancestors of the path."""
        raise NotImplementedError

    @property
    def parent(self) -> SHVPath:
        """The logival parent of the path."""
        if self._parts:
            return type(self)(*self._parts[:-1])
        return self

    @property
    def name(self) -> str:
        """A string representing the final path component, if any."""
        return self._parts[-1] if self._parts else ""

    @property
    def suffix(self) -> str:
        """The last dot-separated portion of the final component, if any."""
        _, dot, suffix = self.name.rpartition(".")
        return f"{dot}{suffix}"

    @property
    def suffixes(self) -> list[str]:
        """The last dot-separated portion of the final component, if any."""
        return list(f".{s}" for s in self.name.split(".")[1:])

    @property
    def stem(self) -> str:
        """The final path component, without its suffix."""
        return self.name.partition(".")[0]

    def is_relative_to(self, path: str | os.PathLike | SHVPath) -> bool:
        """Return whether or not this path is relative to the other path."""
        if not isinstance(path, SHVPath):
            path = SHVPath(path)
        return path._parts[: len(self._parts)] == self._parts

    def joinpath(self, *pathsegments: str | os.PathLike) -> SHVPath:
        """Join paths toggether.

        Calling this method is equivalent to combining the path with each of
        the given pathsegments in turn.
        """
        return type(self)(self, *pathsegments)

    def full_match(self, pattern: str) -> bool:
        """Match this path against the provided glob-style pattern."""
        return shv.rpcri.shvpath_match(pattern, str(self))

    def match(self, pattern: str) -> bool:
        """Match this path against the provided non-recursive glob-style pattern."""
        return any(
            shv.rpcri.shvpath_match(pattern, str(path))
            for path in itertools.takewhile(
                bool, more_itertools.iterate(lambda p: p.parent, self)
            )
        )

    def relative_to(self, other: str | os.PathLike | SHVPath) -> SHVPath:
        """Compute a version of this path relative to the path represented by other."""
        if not isinstance(other, SHVPath):
            other = SHVPath(other)
        if self._parts[: len(other._parts)] != other._parts:
            raise ValueError(f"{self} is not relative to {other}")
        return SHVPath(*self._parts[len(other._parts) :])

    def with_name(self, name: str) -> SHVPath:
        """Return a new path with the name changed."""
        if not self._parts:
            raise ValueError("Root path has an empty name.")
        return type(self)(*self._parts[:-1], name)

    def with_stem(self, stem: str) -> SHVPath:
        """Return a new path with the stem changed."""
        if not self._parts:
            raise ValueError("Root path has an empty name.")
        _, dot, suffix = self._parts[-1].partition(".")
        return type(self)(*self._parts[:-1], f"{stem}{dot}{suffix}")

    def with_suffix(self, suffix: str) -> SHVPath:
        """Return a new path with the suffix changed."""
        if not self._parts:
            raise ValueError("Root path has an empty name.")
        stem, _, _ = self._parts[-1].partition(".")
        return type(self)(*self._parts[:-1], f"{stem}{suffix}")
