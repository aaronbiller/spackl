import mock
import pytest

from google.cloud.bigquery.table import Row
from sqlalchemy.engine import ResultProxy


class mock_engine:
    def __init__(self, url, **kwargs):
        self.url = str(url)
        self._execution_options = dict()

    def execution_options(self, **kwargs):
        self._execution_options.update(**kwargs)

    def connect(self):
        return self

    def close(self):
        pass

    def execute(self, sql, **kwargs):
        result = mock.MagicMock(spec=ResultProxy)
        result.__iter__.return_value = [{'first': 'a', 'second': 'b', 'third': 'c'},
                                        {'first': 'd', 'second': 'e', 'third': 'f'},
                                        {'first': 'g', 'second': 'h', 'third': 'i'}]
        result.keys.return_value = ['first', 'second', 'third']
        return result

    def begin(self):
        return self

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass


@pytest.fixture()
def mock_create_engine():
    def _create_engine(url, **kwargs):
        return mock_engine(url, **kwargs)

    return _create_engine


@pytest.fixture()
def mock_bq_query_result():
    return [
        Row(['a', 'b', 'c'], {'first': 0, 'second': 1, 'third': 3}),
        Row(['d', 'e', 'f'], {'first': 0, 'second': 1, 'third': 3}),
        Row(['g', 'h', 'i'], {'first': 0, 'second': 1, 'third': 3}),
    ]
