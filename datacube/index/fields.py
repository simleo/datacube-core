# coding=utf-8
"""
Common datatypes for DB drivers.
"""
from __future__ import absolute_import


# For the search API.
from datacube.model import Range


class Field(object):
    """
    A searchable field within a dataset/storage metadata document.
    """

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __eq__(self, value):
        """
        Is this field equal to a value?
        :rtype: Expression
        """
        raise NotImplementedError('equals expression')

    def between(self, low, high):
        """
        Is this field in a range?
        :rtype: Expression
        """
        raise NotImplementedError('between expression')


class Expression(object):
    # No properties at the moment. These are built and returned by the
    # DB driver (from Field methods), so they're mostly an opaque token.

    # A simple equals implementation for comparison in test code.
    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.__dict__ == other.__dict__


class OrExpression(Expression):
    def __init__(self, *exprs):
        super(OrExpression, self).__init__()
        self.exprs = exprs


def _to_expression(get_field, name, value):
    field = get_field(name)
    if field is None:
        raise RuntimeError('Unknown field %r' % name)

    if isinstance(value, Range):
        return field.between(value.begin, value.end)
    if isinstance(value, list):
        return OrExpression(*[_to_expression(get_field, name, val) for val in value])
    else:
        return field == value


def to_expressions(get_field, **query):
    """
    Convert a simple query (dict of param names and values) to expression objects.
    :type get_field: (str) -> Field
    :type query: dict[str,str|float|datacube.model.Range]
    :rtype: list[Expression]
    """
    return [_to_expression(get_field, name, value) for name, value in query.items()]


def check_field_equivalence(fields, name):
    """
    :type fields: list[(str, object, object)]
    :type name: str

    >>> check_field_equivalence([('f1', 1, 1)], 'letters')
    >>> check_field_equivalence([('f1', 1, 1), ('f2', 1, 1)], 'letters')
    >>> check_field_equivalence([('f1', 1, 2)], 'Letters')
    Traceback (most recent call last):
    ...
    ValueError: Letters differs from stored (f1)
    >>> check_field_equivalence([('f1', 'a', 'b'), ('f2', 'c', 'd')], 'Letters')
    Traceback (most recent call last):
    ...
    ValueError: Letters differs from stored (f1, f2)
    """
    comparison_errors = {}
    for key, val1, val2 in fields:
        if val1 != val2:
            comparison_errors[key] = (val1, val2)
    if comparison_errors:
        raise ValueError(
            '{} differs from stored ({})'.format(
                name,
                ', '.join(sorted(comparison_errors.keys()))
            )
        )
