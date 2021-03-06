import itertools
from urllib.parse import urlparse, ParseResult
import inspect
import typing

import enum
import dataclasses
from typing import Any, Dict, Generic, List, MutableMapping, Mapping, Tuple, Type, Union, TypeVar, Sequence
from collections.abc import Iterable
from datetime import datetime


TNormal = Union[Dict[str, "TNormal"],
                List["TNormal"], bool, int, float, str, None]

T = TypeVar('T')
TC = Type[T]


class Converter:
    def can_convert(self, typeof):
        "is this evil"

    def convert(self, value, typeof):
        "do conversion of value to type"


def get_args(typeof) -> typing.Tuple[typing.Type]:
    if typeof == list:
        return (typing.Any, )

    if typeof == typing.Dict:
        return (typing.Any, typing.Any)

    if typeof is typing._SpecialForm:
        return tuple(typeof._subs_tree()[1:])

    if type(typeof) == typing._GenericAlias:
        return typeof.__args__
    if hasattr(typing, "_UnionGenericAlias") and type(typeof) == getattr(typing, "_UnionGenericAlias"):
        return typeof.__args__

    raise TypeError(f"can't find type args for {typeof}")


def is_any(typeof):
    return typeof == typing.Any


def cast_any(value, typeof):
    return value


def is_list(typeof):
    if typeof == list:
        return True
    if is_generic_alias(typeof) and typeof._name in ["List"]:
        return True
    return False


def cast_list(value, typeof):
    (list_type, ) = get_args(typeof)
    return [cast(v, list_type) for v in value]


def is_class(typeof):
    return inspect.isclass(typeof)


def cast_class(value, typeof, *, strict=True):
    attrs = typing.get_type_hints(typeof)
    out = typeof()
    assert attrs.keys() >= value.keys(), "source has unkown key type"
    for attr, typeof in attrs.items():
        if attr in value:
            value = value[attr]
            setattr(out, attr, cast(typeof, value))
        elif not hasattr(out, attr):
            raise Exception(f"{typeof} missing required value for {attr}")
    return out


def is_generic_alias(typeof):
    if hasattr(typing, "_SpecialGenericAlias") and type(typeof) == getattr(typing, "_SpecialGenericAlias"):
        return True
    return type(typeof) in [typing._GenericAlias]


def is_enum(typeof):
    return is_class(typeof) and issubclass(typeof, enum.Enum)


def cast_enum(value, typeof):
    return typeof[value]


def is_union(typeof):
    if typeof is typing._SpecialForm and typeof._name == 'Union':
        return True
    if hasattr(typing, "_UnionGenericAlias") and type(typeof) == getattr(typing, "_UnionGenericAlias"):
        return True
    if type(typeof) == typing._GenericAlias:
        typename = typeof._name
        if typename == "Union":
            return True
        if typename is None and typeof.__origin__ == typing.Union:
            return True
    return False


def cast_union(value, typeof):
    typeofs = get_args(typeof)
    for typeof in typeofs:
        try:
            return cast(value, typeof)
        except:
            pass
    raise TypeError(f"{value} not any of valid types {typeofs}")


def is_dict(typeof):
    if typeof == dict:
        return True
    if is_generic_alias(typeof) and typeof._name in ["Dict", "MutableMapping", "Mapping"]:
        return True
    return False


def cast_dict(value, typeof):
    (kt, vt) = get_args(typeof)
    return {cast(k, kt): cast(v, vt) for k, v in value.items()}


def is_none(typeof):
    return typeof == None or is_class(typeof) and typeof.__name__ == "NoneType"


def cast_none(value, typeof):
    return None


def is_int(typeof):
    return typeof == int


def is_float(typeof):
    return typeof == float


def is_bool(typeof):
    return typeof == bool


def is_str(typeof):
    return typeof == str


def is_datetime(typeof):
    return typeof == datetime


def cast_datetime(value, typeof):
    assert value is str
    return datetime.fromisoformat(value)


def cast_primitive(value, typeof):
    if value is None:
        raise TypeError(f"none is not castable to {typeof}")
    return typeof(value)


def is_dataclass(typeof):
    #assert isinstance(typeof, type)
    return dataclasses.is_dataclass(typeof)


def cast_dataclass(value, typeof, *, strict=True):
    as_dict = {field.name: cast(value[field.name], field.type)
               for field in dataclasses.fields(typeof) if field.name in value}
    return typeof(**as_dict)


def is_url(typeof):
    return typeof == ParseResult


def cast_url(value, typeof):
    "cast a string to a uri"
    return urlparse(value)


CASTERS = [
    (is_none, cast_none),
    (is_int, cast_primitive),
    (is_float, cast_primitive),
    (is_bool, cast_primitive),
    (is_str, cast_primitive),
    (is_datetime, cast_datetime),
    (is_url, cast_url),
    (is_enum, cast_enum),
    (is_dict, cast_dict),
    (is_list, cast_list),
    (is_union, cast_union),
    (is_dataclass, cast_dataclass),
    (is_class, cast_class)
]




def most(v):
    return v[:-1]

def last(v):
    return v[-1]

def first(v):
    return v[0]


def iter_most(v):
    return v[:-1]

def iter_last(v):
    return v[-1]

def iter_first(v):
    return v[0]

def first_rest(v):
    return (first(v), rest(v))

def renest(stuff):
    for key, v in stuff:
        key_head = key[0]
        key_rest = key[1:]

def normal_roughen(flat_str: Dict[str, str]):
    "deflatten a dict flattend by normal_flatten into a normal form object"
    flat = {parse_flat_path(k) : literal_eval(v) for k,v in flat_str.items()}
    
    values = {}

    sorted_flat = sorted(flat, key = len)

    for key, value in sorted_flat:
        values[key] = value
        for i in range(len(key)-1):
            subkey = key[:i]
            last = subkey[i]
            if last is int:
                values[subkey] = list()
            elif last is dict:
                values[subkey] = dict()
            else:
                raise TypeError(f"did not expect {last} in path")
    

def cast(value: TNormal, typeof: Type[T], strict: bool = True) -> T:
    for test, caster in CASTERS:
        if(test(typeof)):
            return caster(value, typeof)
    raise TypeError(f"can't cast {value} to {typeof}")


def normal(value: Any) -> TNormal:
    """
    Convert a python object to normal form (so it can be json serlized)
    normal form is 
    """
    if value is None:
        return None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): normal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normal(v) for v in value]
    if isinstance(value, enum.Enum):
        return value.name
    if dataclasses.is_dataclass(value):
        return normal(dataclasses.asdict(value))
    return normal(value.__dict__)


__all__ = ["cast", "normal"]
