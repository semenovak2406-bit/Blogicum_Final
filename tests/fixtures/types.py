from typing import TypeVar, Union

from tests.adapters.post import PostModelAdapter
from tests.adapters.user import UserModelAdapter

CommentModelAdapterT = TypeVar("CommentModelAdapterT", bound=type)
ModelAdapterT = Union[CommentModelAdapterT, PostModelAdapter, UserModelAdapter]
