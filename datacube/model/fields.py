"""Non-db specific implementation of metadata search fields.

This allows extraction of fields of interest from dataset metadata document.
"""
import toolz
import decimal
from datacube.utils import parse_time
from datacube.model import Range


class SimpleField(object):
    def __init__(self,
                 offset,
                 converter,
                 type_name,
                 name='',
                 description=''):
        self._offset = offset
        self._converter = converter
        self.type_name = type_name
        self.description = description
        self.name = name

    def extract(self, doc):
        v = toolz.get_in(self._offset, doc, default=None)
        if v is None:
            return None
        return self._converter(v)


class RangeField(object):
    def __init__(self,
                 min_offset,
                 max_offset,
                 base_converter,
                 type_name,
                 name='',
                 description=''):
        self.type_name = type_name
        self.description = description
        self.name = name
        self._converter = base_converter
        self._min_offset = min_offset
        self._max_offset = max_offset

    def extract(self, doc):
        def extract_raw(paths):
            vv = [toolz.get_in(p, doc, default=None) for p in paths]
            return [self._converter(v) for v in vv if v is not None]

        v_min = extract_raw(self._min_offset)
        v_max = extract_raw(self._max_offset)

        v_min = None if len(v_min) == 0 else min(v_min)
        v_max = None if len(v_max) == 0 else max(v_max)

        if v_min is None and v_max is None:
            return None

        return Range(v_min, v_max)


def parse_search_field(doc, name=''):
    parsers = {
        'string': str,
        'double': float,
        'integer': int,
        'numeric': decimal.Decimal,
        'datetime': parse_time,
        'object': lambda x: x,
    }
    _type = doc.get('type', 'string')

    if _type in parsers:
        offset = doc.get('offset', None)
        if offset is None:
            raise ValueError('Missing offset')

        return SimpleField(offset,
                           parsers[_type],
                           _type,
                           name=name,
                           description=doc.get('description', ''))

    if not _type.endswith('-range'):
        raise ValueError('Unsupported search field type: ' + str(_type))

    raw_type = _type.split('-')[0]

    if raw_type == 'float':  # float-range is supposed to be supported, but not just float?
        raw_type = 'numeric'
        _type = 'numeric-range'

    if raw_type not in parsers:
        raise ValueError('Unsupported search field type: ' + str(_type))

    min_offset = doc.get('min_offset', None)
    max_offset = doc.get('max_offset', None)

    if min_offset is None or max_offset is None:
        raise ValueError('Need to specify both min_offset and max_offset')

    return RangeField(min_offset,
                      max_offset,
                      parsers[raw_type],
                      _type,
                      name=name,
                      description=doc.get('description', ''))


def get_dataset_fields(metadata_definition):
    """Construct search fields dictionary not tied to any specific db
    implementation.

    """
    fields = toolz.get_in(['dataset', 'search_fields'], metadata_definition, {})
    return {n: parse_search_field(doc, name=n) for n, doc in fields.items()}
