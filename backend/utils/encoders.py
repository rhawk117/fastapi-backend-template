from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address
from pathlib import Path, PurePath
from typing import Any

import msgspec
from pydantic import BaseModel
from sqlalchemy.engine.row import Row

type EncodableResponses = BaseModel | dict | list | str | bytes | msgspec.Struct


def msgspec_encoder_hook(obj: Any) -> Any:
    """Handles any type not already handled by msgspec's default JSON encoder.

    Parameters
    ----------
    obj : Any
        The object to serialize.

    Returns
    -------
    Any
        The serialized object.

    Raises
    ------
    NotImplementedError
        If the object type is not supported for
        serialization.
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump(
            mode='json',
            exclude_none=True,
            by_alias=True,
        )

    if isinstance(obj, (Path, PurePath)):
        return str(obj)

    if isinstance(obj, (IPv4Address, IPv6Address)):
        return str(obj)

    if isinstance(obj, Row):
        return dict(obj._mapping)

    raise NotImplementedError(
        f'response_enc_hook: {type(obj)} not supported for serialization'
    )


JSONEncoder = msgspec.json.Encoder(
    enc_hook=msgspec_encoder_hook,
    uuid_format='canonical',
    order='sorted',
    decimal_format='string',
)
MsgpackEncoder = msgspec.msgpack.Encoder(
    enc_hook=msgspec_encoder_hook,
    uuid_format='canonical',
    order='sorted',
    decimal_format='string',
)
