# RATBOT's tiny asyncpg wrapper.
# Adapted from catpg (MIT License, Copyright (c) 2026 Lia Milenakos & Cat Bot Contributors),
# used here under the terms of that license.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from collections.abc import AsyncGenerator, Sequence
from typing import Any, ClassVar, Self

import asyncpg

AnyConnection = asyncpg.Connection | asyncpg.pool.PoolConnectionProxy | asyncpg.Pool

pool: asyncpg.Pool | None = None


def _get_pool() -> asyncpg.Pool:
    assert pool is not None, "Not connected. Call connect() first."
    return pool


async def connect(dsn: str, min_size: int = 1, max_size: int = 5) -> None:
    global pool
    pool = await asyncpg.create_pool(dsn=dsn, min_size=min_size, max_size=max_size)


async def close() -> None:
    if pool:
        await pool.close()


class Model:
    """Composite-primary-key models must set `_pk` to a tuple of column names.
    Set `_table` if the table name isn't just the class name lowercased."""

    _pk: ClassVar[Sequence[str]] = ("id",)
    _table: ClassVar[str | None] = None

    @classmethod
    def _table_name(cls) -> str:
        return cls._table or cls.__name__.lower()

    def __init__(self, record: asyncpg.Record) -> None:
        self.__dirty: list[str] = []
        self.__values: dict[str, Any] = dict(record.items())

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_Model__") or name.startswith("_"):
            return super().__setattr__(name, value)
        if name not in self.__values:
            raise KeyError(name)
        if value != self.__values[name] and name not in self.__dirty:
            self.__dirty.append(name)
        self.__values[name] = value

    def __getattr__(self, name: str) -> Any:
        try:
            return self.__values[name]
        except KeyError:
            raise AttributeError(name) from None

    def __getitem__(self, name: str) -> Any:
        return self.__values[name]

    def _pk_where(self, start: int = 1) -> tuple[str, list[Any]]:
        clauses = [f'"{col}" = ${i}' for i, col in enumerate(self._pk, start=start)]
        values = [self.__values[col] for col in self._pk]
        return " AND ".join(clauses), values

    async def save(self, connection: AnyConnection | None = None) -> None:
        if not self.__dirty:
            return
        table = self._table_name()
        conn = connection or _get_pool()
        set_clauses = []
        args: list[Any] = []
        for i, col in enumerate(self.__dirty, start=1):
            set_clauses.append(f'"{col}" = ${i}')
            args.append(self.__values[col])
        where, pk_args = self._pk_where(start=len(args) + 1)
        args.extend(pk_args)
        query = f'UPDATE "{table}" SET {", ".join(set_clauses)} WHERE {where};'
        await conn.execute(query, *args)
        self.__dirty = []

    async def delete(self, connection: AnyConnection | None = None) -> None:
        table = self._table_name()
        conn = connection or _get_pool()
        where, args = self._pk_where()
        await conn.execute(f'DELETE FROM "{table}" WHERE {where};', *args)

    @classmethod
    async def get_or_none(cls, connection: AnyConnection | None = None, **kwargs) -> Self | None:
        table = cls._table_name()
        conn = connection or _get_pool()
        clauses = [f'"{k}" = ${i}' for i, k in enumerate(kwargs, start=1)]
        query = f'SELECT * FROM "{table}" WHERE {" AND ".join(clauses)} LIMIT 1;'
        record = await conn.fetchrow(query, *kwargs.values())
        return cls(record) if record else None

    @classmethod
    async def get_or_create(cls, connection: AnyConnection | None = None, defaults: dict[str, Any] | None = None, **kwargs) -> Self:
        conn = connection or _get_pool()
        existing = await cls.get_or_none(connection=conn, **kwargs)
        if existing:
            return existing
        return await cls.create(connection=conn, **{**kwargs, **(defaults or {})})

    @classmethod
    async def create(cls, connection: AnyConnection | None = None, **kwargs) -> Self:
        table = cls._table_name()
        conn = connection or _get_pool()
        columns = list(kwargs.keys())
        col_names = ", ".join(f'"{c}"' for c in columns)
        placeholders = ", ".join(f"${i}" for i in range(1, len(columns) + 1))
        query = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) RETURNING *;'
        record = await conn.fetchrow(query, *kwargs.values())
        assert record is not None
        return cls(record)

    @classmethod
    async def filter(cls, where: str | None = None, *args, connection: AnyConnection | None = None) -> AsyncGenerator[Self, None]:
        table = cls._table_name()
        conn = connection or _get_pool()
        query = f'SELECT * FROM "{table}"'
        if where:
            query += f" WHERE {where}"
        for row in await conn.fetch(query + ";", *args):
            yield cls(row)

    @classmethod
    async def collect(cls, where: str | None = None, *args, connection: AnyConnection | None = None) -> list[Self]:
        return [row async for row in cls.filter(where, *args, connection=connection)]
