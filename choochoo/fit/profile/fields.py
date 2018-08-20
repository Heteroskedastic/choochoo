
from collections import namedtuple
from itertools import repeat

from .support import Named
from ...lib.data import WarnDict

TIMESTAMP_GLOBAL_TYPE = 253


class ScaledField(Named):

    def __init__(self, log, name, units, scale, offset, accumulate):
        super().__init__(log, name)
        self._units = units
        self._scale = 1 if scale is None else scale
        self._offset = 0 if offset is None else offset
        self._is_scaled = self._scale != 1 or self._offset != 0
        self._is_accumulate = accumulate

    def _parse_and_scale(self, type, data, count, endian, accumulate):
        values = type.parse(data, count, endian)
        if values is not None:
            if self._is_scaled:
                if any(isinstance(value, str) for value in values) or isinstance(self._scale, str):
                    print('x')
                values = tuple(value / self._scale - self._offset for value in values)
            if self._is_accumulate:
                values = accumulate(self, values)
        yield self.name, (values, self._units)


class TypedField(ScaledField):

    def __init__(self, log, name, field_no, units, scale, offset, accumulate, field_type, types):
        super().__init__(log, name, units, scale, offset, accumulate)
        self.number = field_no
        self.type = types.profile_to_type(field_type)

    def parse(self, data, count, endian, references, accumulate, message):
        yield from self._parse_and_scale(self.type, data, count, endian, accumulate)


class RowField(TypedField):

    def __init__(self, log, row, types):
        super().__init__(log, row.field_name, row.single_int(log, row.field_no), row.units,
                         row.single_int(log, row.scale), row.single_int(log, row.offset),
                         row.single_int(log, row.accumulate), row.field_type, types)


class DelegateField(ScaledField):

    def parse(self, data, count, endian, references, accumulate, message):
        # todo - do we need to worry about padding data?
        delegate = message.profile_to_field(self.name)
        if isinstance(delegate, RowField):
            yield from self._parse_and_scale(delegate.type, data, count, endian, accumulate)
        else:
            # on dangerous ground here.  docs are unclear.  we'll do a complete delegation
            # unless this is scaled, in which case we don't know how to both scale and
            # delegate
            if self._is_scaled:
                raise Exception('Scaled component is not a simple field')
            else:
                yield from delegate.parse(data, count, endian, references, accumulate, message)

    def size(self, message):
        delegate = message.profile_to_field(self.name)
        return delegate.type.size


class Zip:

    def _zip(self, *fields):
        return zip(*(self.__split(field, extend=n > 1) for n, field in enumerate(fields)))

    def __split(self, field, extend=False):
        if field:
            for value in str(field).split(','):
                yield value.strip()
        else:
            yield None
        if extend:
            yield from repeat(None)


class CompositeField(Zip, Named):

    def __init__(self, log, row):
        super().__init__(log, row.field_name)
        self.number = row.single_int(log, row.field_no)
        self.__components = []
        for (name, bits, units, scale, offset, accumulate) in \
                self._zip(row.components, row.bits, row.units, row.scale, row.offset, row.accumulate):
            self.__components.append((int(bits),
                                      DelegateField(log, name, units,
                                                    None if scale is None else float(scale),
                                                    None if offset is None else float(offset),
                                                    accumulate)))

    def parse(self, data, count, endian, references, accumulate, message):
        byteorder = ['little', 'big'][endian]
        bits = int.from_bytes(data, byteorder=byteorder)
        for nbits, field in self.__components:
            nbytes = max((nbits+7) // 8, field.size(message))
            data = (bits & ((1 << bits) - 1)).to_bytes(nbytes, byteorder=byteorder)
            bits >>= nbits
            yield from field.parse(data, 1, endian, references, accumulate, message)


class DynamicField(Zip, RowField):

    def __init__(self, log, row, rows, types):
        super().__init__(log, row, types)
        self.__dynamic_lookup = WarnDict(log, 'No dynamic field for %r')
        self.references = set()
        for row in rows.lookahead():
            if row and row.field_name and row.field_no is None:
                for name, value in self._zip(row.ref_name, row.ref_value):
                    self.references.add(name)
                    self.__dynamic_lookup[(name, value)] = row.field_name
            else:
                break

    def parse(self, data, count, endian, references, accumulate, message):
        for name in self.references:
            if name in references:
                lookup = (name, references[name][0][0])  # drop units and take first value
                if lookup in self.__dynamic_lookup:
                    yield from message.profile_to_field(self.__dynamic_lookup[lookup]).parse(
                        data, count, endian, references, accumulate, message)
                    return
        self._log.warn('Could not resolve dynamic field %s' % self.name)
        yield from super().parse(data, count, endian, references, accumulate, message)


def MessageField(log, row, rows, types):
    # log.debug('Parsing field %s' % row.field_name)
    if row.components:
        return CompositeField(log, row)
    else:
        peek = rows.peek()
        if peek and peek.field_name and peek.field_no is None:
            return DynamicField(log, row, rows, types)
        else:
            return RowField(log, row, types)


class Row(namedtuple('BaseRow',
                     'msg_name, field_no, field_name, field_type, array, components, scale, offset, ' +
                     'units, bits, accumulate, ref_name, ref_value, comment, products, example')):

    __slots__ = ()

    def __new__(cls, row):
        return super().__new__(cls, *tuple(row)[0:16])

    def single_int(self, log, value):
        try:
            return None if value is None else int(value)
        except ValueError:
            log.warn('Cannot parse "%s" as a single integer', value)
            return None
