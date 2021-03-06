import os

from spackl.util import ABC, abstractmethod


def get_default_db_conn_kwargs():
    """
        Generate dummy kwargs for a default connection
    """
    uname = os.uname()[1]
    return {
        'database': uname,
        'username': uname,
        'password': None,
        'host': 'localhost',
        'port': 5432
    }


class BaseDb(ABC):
    _connected = False
    _conn = None
    _db_type = None
    _conn_kwargs = None

    @property
    def connected(self):
        return self._connected

    @abstractmethod
    def _connect(self):
        """
            Connect to the source database

            Should set self._conn with the connection object
        """
        raise NotImplementedError()

    def connect(self):
        """Connect to the source database

        Returns:
            None
        """
        if not self._connected:
            self._connect()
        if self._conn:
            self._connected = True

    @abstractmethod
    def _close(self):
        """
            Close any open connection
        """
        raise NotImplementedError()

    def close(self):
        """Close any open connection
        """
        if self._conn:
            self._close()
        self._conn = None
        self._connected = False

    @abstractmethod
    def query(self, query_string, **kwargs):
        """
            Runs a query against the source database and returns the results

            If not connected, should call self.connect() first

            Args:
                query_string : str - The query to run against the database

            Kwargs:
                kwargs : Arbitrary parameters to pass to the query engine

            Returns:
                QueryResult containing the query result
        """
        raise NotImplementedError()

    @abstractmethod
    def execute(self, query_string, **kwargs):
        """
            Runs a query against the source database, intended for DDL, Insert/Update/Delete

            If not connected, should call self.connect() first

            Args:
                query_string : str - The query to run against the database

            Kwargs:
                kwargs : Arbitrary parameters to pass to the query engine

            Returns:
                None
        """
        raise NotImplementedError()
