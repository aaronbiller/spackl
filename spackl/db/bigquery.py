"""
    Class for using Google BigQuery as a source database
"""
import logging
import os
import six

from google.cloud.bigquery import Client

from spackl.util import Path

from .base import BaseDb

_log = logging.getLogger(__name__)


BIGQUERY_DEFAULT_CONN_KWARGS = {
    'project': None,
    'credentials': None,
    'location': None
}


class BigQuery(BaseDb):
    """
        A Google BigQuery database client

        Kwargs:
            name : str - The canonical name to use for this instance
            creds_file : str - The filepath of the desired GOOGLE_APPLICATION_CREDENTIALS file
            conn_kwargs : Use in place of a query string to set individual
                          attributes of the connection defaults (project, etc)
    """

    def __init__(self, name=None, creds_file=None, **conn_kwargs):
        if creds_file is None:
            creds_file = os.getenv('BIGQUERY_CREDS_FILE', None)
        self._bq_creds_file = creds_file

        self._conn_kwargs = dict(**BIGQUERY_DEFAULT_CONN_KWARGS)

        self._name = name
        for k, v in six.iteritems(conn_kwargs):
            if k in self._conn_kwargs:
                self._conn_kwargs[k] = v

    def __repr__(self):
        return '<{db.__class__.__name__}({project})>'.format(db=self, project=self._conn_kwargs['project'])

    @property
    def name(self):
        return self._name

    @property
    def project(self):
        return self._conn_kwargs['project']

    @project.setter
    def project(self, value):
        self._conn_kwargs['project'] = value

    def _connect(self):
        if self._bq_creds_file is not None:
            if Path(self._bq_creds_file).exists():
                os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', self._bq_creds_file)
            else:
                _log.warning('Path set by creds file does not exist: %s', self._bq_creds_file)
        self._conn = Client(**self._conn_kwargs)

    def _close(self):
        """
            This is a no-op because the bigquery Client doesn't have a close method.
            The BaseDb close method will handle setting self._conn to None and self._connected to False.
        """
        return

    def _query(self, query_string):
        self.connect()
        query_job = self._conn.query(query_string)
        return query_job.result()

    def query(self, query_string):
        from .result import QueryResult
        result = self._query(query_string)
        return QueryResult(result)

    def execute(self, query_string):
        self._query(query_string)

    def list_tables(self, dataset_id):
        """
            List all tables in the provided dataset

            Args:
                dataset_id : str - The dataset to query

            Returns:
                list of table names
        """
        self.connect()
        dataset_ref = self._conn.dataset(dataset_id)
        return [t.table_id for t in self._conn.list_tables(dataset_ref)]

    def delete_table(self, dataset_id, table_id):
        """
            Delete the given table in the given dataset

            Args:
                dataset_id : str - The dataset containing the table to delete
                table_id : str - The table to delete

            Returns:
                None
        """
        self.connect()
        table_ref = self._conn.dataset(dataset_id).table(table_id)
        self._conn.delete_table(table_ref)
