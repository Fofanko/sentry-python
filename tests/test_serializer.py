import sys
import pytest

from sentry_sdk.serializer import serialize

try:
    from hypothesis import given
    import hypothesis.strategies as st
except ImportError:
    pass
else:

    def test_bytes_serialization_decode_many(message_normalizer):
        @given(binary=st.binary(min_size=1))
        def inner(binary):
            result = message_normalizer(binary, should_repr_strings=False)
            assert result == binary.decode("utf-8", "replace")

        inner()

    def test_bytes_serialization_repr_many(message_normalizer):
        @given(binary=st.binary(min_size=1))
        def inner(binary):
            result = message_normalizer(binary, should_repr_strings=True)
            assert result == repr(binary)

        inner()


@pytest.fixture
def message_normalizer(validate_event_schema):
    def inner(message, **kwargs):
        event = serialize({"logentry": {"message": message}}, **kwargs)
        validate_event_schema(event)
        return event["logentry"]["message"]

    return inner


@pytest.fixture
def extra_normalizer(validate_event_schema):
    def inner(message, **kwargs):
        event = serialize({"extra": {"foo": message}}, **kwargs)
        validate_event_schema(event)
        return event["extra"]["foo"]

    return inner


def test_bytes_serialization_decode(message_normalizer):
    binary = b"abc123\x80\xf0\x9f\x8d\x95"
    result = message_normalizer(binary, should_repr_strings=False)
    assert result == u"abc123\ufffd\U0001f355"


@pytest.mark.xfail(sys.version_info < (3,), reason="Known safe_repr bugs in Py2.7")
def test_bytes_serialization_repr(message_normalizer):
    binary = b"abc123\x80\xf0\x9f\x8d\x95"
    result = message_normalizer(binary, should_repr_strings=True)
    assert result == r"b'abc123\x80\xf0\x9f\x8d\x95'"


def test_serialize_sets(extra_normalizer):
    result = extra_normalizer({1, 2, 3})
    assert result == [1, 2, 3]


def test_serialize_custom_mapping(extra_normalizer):
    class CustomReprDict(dict):
        def __sentry_repr__(self):
            return "custom!"

    result = extra_normalizer(CustomReprDict(one=1, two=2))
    assert result == "custom!"


def test_custom_mapping_doesnt_mess_with_mock(extra_normalizer):
    """
    Adding the __sentry_repr__ magic method check in the serializer
    shouldn't mess with how mock works. This broke some stuff when we added
    sentry_repr without the dunders.
    """
    mock = pytest.importorskip("unittest.mock")
    m = mock.Mock()
    extra_normalizer(m)
    assert len(m.mock_calls) == 0
