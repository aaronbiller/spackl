import copy
import json
import six

from spackl.util import DtDecEncoder


class ResultRow(object):
    """
        A container object providing functionality and syntactic sugar
        on top of a single row of a query result

        Args:
            keys : list - The keys (AKA column names) of the query result
            row : OrderedDict - The row of data from the query result
    """
    __slots__ = ['_keys', '_row']

    def __init__(self, keys, row):
        self._keys = keys
        self._row = row

    def __repr__(self):
        return str(tuple([v for v in self.values()]))

    def __str__(self):
        return self.__repr__()

    def __bool__(self):
        return bool(self._row)

    __nonzero__ = __bool__

    def __getattr__(self, name):
        return self.__getitem__(str(name))

    def __getitem__(self, key):
        if isinstance(key, six.string_types):
            # Return the column corresponding with this key
            if key not in self._keys:
                raise KeyError('Not found : %r' % key)
            value = self._row[key]
        elif isinstance(key, six.integer_types):
            # Return the column corresponding with this index
            k = self._keys[key]
            value = self._row[k]
        else:
            raise TypeError('Lookups must be done with integers or strings, not %s' % type(key))
        return value

    def __eq__(self, other):
        if not isinstance(other, ResultRow):
            return NotImplemented
        return self._row == other._row

    def __ne__(self, other):
        return not self == other

    def values(self):
        return tuple(six.itervalues(self._row))

    def keys(self):
        return list(six.iterkeys(self._row))

    def items(self):
        for key, value in six.iteritems(self._row):
            yield (key, value)

    def get(self, key, default=None):
        value = self._row.get(key)
        if value is None:
            return default
        return value


class ResultCol(object):
    """
        A container object providing functionality and syntactic sugar
        on top of a single column of a query result

        Args:
            key : str - The key (AKA column name) of the query result
            col : tuple - The column of data from the query result
    """
    __slots__ = ['_index', '_key', '_col']

    def __init__(self, key, col):
        self._key = key
        self._col = col

    def __repr__(self):
        return str(self._col)

    def __str__(self):
        # Calling str() on string type values to avoid unicode strings in python 2
        return str(tuple([str(v) if isinstance(v, six.string_types) else v for v in self._col]))

    def __bool__(self):
        return bool(self._col)

    __nonzero__ = __bool__

    def __iter__(self):
        self._index = 0
        return self

    def __next__(self):
        self._index += 1
        try:
            col = self._col[self._index - 1]
        except IndexError:
            raise StopIteration
        return col

    next = __next__

    def __getattr__(self, name):
        return self.__getitem__(str(name))

    def __getitem__(self, key):
        if isinstance(key, six.string_types):
            # Return the column corresponding with this key
            if key != self._key:
                raise KeyError('Not found : %r' % key)
            value = copy.deepcopy(self._col)
        elif isinstance(key, six.integer_types):
            # Return the row corresponding with this index
            value = self._col[key]
        elif isinstance(key, slice):
            # Return the rows corresponding with this slice
            sliced = [self._col[ii] for ii in range(*key.indices(len(self._col)))]
            value = tuple(sliced)
        else:
            raise TypeError('Lookups must be done with integers or strings, not %s' % type(key))
        return value

    def __len__(self):
        return len(self._col)

    def __eq__(self, other):
        if not isinstance(other, ResultCol):
            return NotImplemented
        return self._col == other._col

    def __ne__(self, other):
        return not self == other

    def _rquery_format(self):
        """
            Special method for models.SourcePair to call when formatting the rquery

            Returns:
                str - The properly formatted values of this column
        """
        # Filter out None values
        col = [v for v in self._col if v is not None]
        _len = len(col)

        # Calling str() on string type values to avoid unicode strings in python 2
        if _len == 0:
            # Gracefully handle an empty column
            # Fill the result with a nonsense value to prevent false positives
            return str("('__xxx__EMPTYRESULT__xxx__')")
        elif _len == 1:
            # Handle a single-value column without creating an invalid sql syntax.
            # When formatting the rquery in a SourcePair, using the query with a
            # value like (1,) will raise a syntax error.
            v = col[0]
            if isinstance(v, six.string_types):
                v = "'{}'".format(str(v))
            return str('({})'.format(v))
        else:
            return str(tuple([str(v) if isinstance(v, six.string_types) else v for v in col]))


class BaseResult(object):
    """
        Base class for containing contents of a query result or a file
    """
    __slots__ = ['_index', '_keys', '_result']

    def __init__(self, keys, result):
        if not isinstance(keys, list):
            raise TypeError('Keys must be a list')
        self._keys = keys

        if not isinstance(result, list):
            result = [result]
        self._result = result

    def __repr__(self):
        return '<BaseResult: {br._result}>'.format(br=self)

    def __str__(self):
        return self.json()

    def __bool__(self):
        return bool(self._result)

    __nonzero__ = __bool__

    def __iter__(self):
        self._index = 0
        return self

    def __next__(self):
        self._index += 1
        try:
            row = self._result[self._index - 1]
        except IndexError:
            raise StopIteration
        return ResultRow(self._keys, row)

    next = __next__

    def __getattr__(self, name):
        return self.__getitem__(str(name))

    def __getitem__(self, key):
        if isinstance(key, six.string_types):
            # Return the column corresponding with this key
            if key not in self._keys:
                raise KeyError('Not found : %r' % key)
            col = tuple([row[key] for row in self._result])
            value = ResultCol(key, col)
        elif isinstance(key, six.integer_types):
            # Return the row corresponding with this index
            row = self._result[key]
            value = ResultRow(self._keys, row)
        elif isinstance(key, slice):
            # Return the rows corresponding with this slice
            sliced = [self._result[ii] for ii in range(*key.indices(len(self._result)))]
            value = self._from_part(self._keys, sliced)
        else:
            raise TypeError('Lookups must be done with integers or strings, not %s' % type(key))
        return value

    def __len__(self):
        return len(self._result)

    def __eq__(self, other):
        if not isinstance(other, BaseResult):
            return NotImplemented
        return self._result == other._result

    def __ne__(self, other):
        return not self == other

    @classmethod
    def _from_part(cls, keys, result):
        """
            Get a new BaseResult from an existing sliced or filtered result

            Returns:
                BaseResult
        """
        br = cls([], [])
        br._keys = keys
        br._result = result
        return br

    @property
    def empty(self):
        """
            Check if both the result and keys are empty

            Returns:
                bool
        """
        return bool(not self._keys and not self._result)

    @property
    def result(self):
        """
            Get the full results of the query as a list of dicts

            Returns:
                list of dicts - [{column: value, ... }, ... ]
        """
        return copy.deepcopy(self._result)

    def dict(self):
        """
            Get the full results of the query as a columnar dict

            Returns:
                dict - {column: (value, ... ), ... }
        """
        return {k: tuple([row[k] for row in self._result]) for k in self._keys}

    def json(self):
        """
            Get the full results of the query as a json string

            Returns:
                string
        """
        return json.dumps(self._result, cls=DtDecEncoder)

    def list(self):
        """
            Get the full results of the query as a row-based list of tuples

            Returns:
                list of tuples - [(value, ... ), ... ]
        """
        return [tuple([v for v in six.itervalues(row)]) for row in self._result]

    def df(self, *args, **kwargs):
        """
            Get the full results of the query as a dataframe

            Returns:
                pandas.DataFrame
        """
        from pandas import DataFrame
        return DataFrame(self._result, *args, **kwargs)

    def first(self):
        """
            Get the first row of the result

            Returns:
                QueryResultRow
        """
        return ResultRow(self._keys, self._result[0])

    def values(self):
        for item in self.list():
            yield item

    def keys(self):
        for key in self._keys:
            yield key

    def items(self):
        for key, value in six.iteritems(self.dict()):
            yield (key, value)

    def get(self, key, default=None):
        try:
            value = self.__getitem__(str(key))
        except KeyError:
            return default
        return value

    def pop(self, index=-1):
        """
            Remove and return the row at the given index (default last)

            Args:
                index : int - The index of the row to remove and return

            Returns:
                QueryResultRow
        """
        return ResultRow(self._keys, self._result.pop(index))

    def append(self, other):
        """
            Append a QueryResultRow with matching keys to the current result

            Args:
                other : QueryResultRow - The row to append
        """
        if not isinstance(other, ResultRow):
            raise NotImplementedError('Appending object must be a QueryResultRow')
        if self.empty:
            self._keys = other._keys
        elif self._keys != other._keys:
            raise ValueError('Keys in appending row do not match, cannot append')
        self._result.append(other._row)

    def extend(self, other):
        """
            Extend the current result with another QueryResult with matching keys

            Args:
                other : QueryResult - The row to append
        """
        if not isinstance(other, BaseResult):
            raise NotImplementedError('Extending object must be a QueryResult')
        if self.empty:
            self._keys = other._keys
        elif self._keys != other._keys:
            raise ValueError('Keys in other QueryResult to not match, cannot extend')
        self._result.extend(other._result)

    def filter(self, predicate, inplace=False):
        """
            Filter the query result rows

            Args:
                predicate : callable - The function to apply to each result row, should return a boolean

            Kwargs:
                inplace : boolean - Whether to alter the results in-place or return a new QueryResult object

            Returns:
                QueryResult with filtered results
        """
        filtered = [row for row in self._result if predicate(ResultRow(self._keys, row))]
        if inplace:
            self._result = filtered
            return None
        else:
            return self._from_part(self._keys, filtered)
