import json

from collections.abc import Sequence

from .exceptions import ImproperlyConfigured, ValidationError
from .snapshots import ModelSnapshots
from .utils import (
    cached_property, unspecified, validate_type, OrderedIndexedTransformDict
)


__all__ = [
    'set_related',
    'clear_related',
    'FieldCollection',
    'ModelCollection',
]


def set_related(model, relationship_name, related):
    current_related_value = getattr(model, relationship_name, None)
    if isinstance(current_related_value, ModelCollection):
        current_related_value.add(related)
    else:
        setattr(model, relationship_name, related)


def clear_related(model, relationship_name, related):
    current_related_value = getattr(model, relationship_name, None)
    if isinstance(current_related_value, ModelCollection):
        current_related_value.discard(related)
    elif current_related_value == related:
        setattr(model, relationship_name, None)


class OwnedList(list):
    def __init__(self, iterable=None, owner=None, attrname=None,
                 snapshots=None):
        super(OwnedList, self).__init__()

        def get_key(model):
            try:
                assert len(model) == 2
                return tuple(model)
            except (AssertionError, TypeError):
                pass
            try:
                return model.data_key
            except AttributeError:
                pass
            if isinstance(model, int):
                model = next((m for m, v in self.cache._data.items()
                              if v == model), None)
                if model is not None:
                    return get_key(model)
            elif isinstance(model, str):
                return (self.__class__, model)
            try:
                return ('start-url', (model['type'], model['url']))
            except (TypeError, KeyError):
                pass
            raise TypeError('invalid key: {!r}'.format(model))
        self.cache = OrderedIndexedTransformDict(get_key)
        self.owner = owner and owner.with_snapshots()
        self.attrname = attrname
        self.snapshots = snapshots or ModelSnapshots.default_snapshots
        if (owner is None) != (attrname is None):
            raise ImproperlyConfigured(
                u"To create a {} connected to an instance both 'instance' and "
                u"'attrname' must be provided".format(
                    self.__class__.__name__))
        if iterable:
            self.extend(iterable)

    @cached_property
    def field(self):
        return self.owner._fields[self.attrname]

    def with_snapshots(self, snapshots=None):
        if self.snapshots == (snapshots or ModelSnapshots.default_snapshots):
            return self
        copy = self.__class__(owner=self.owner, attrname=self.attrname,
                              snapshots=snapshots)
        super(OwnedList, copy).extend(self)
        return copy

    def __setitem__(self, index, value):
        is_slice = isinstance(index, slice)
        cache = self.cache
        if is_slice:
            try:
                value = list(value)
            except TypeError:
                TypeError(u"can only assign an iterable")
            for v in value:
                self._validate(v)
                if v in cache:
                    raise ValueError(
                        u"Collection already contains object {}".format(v))
        else:
            self._validate(value)
        try:
            current = self[index]
            changed = value == current
        except IndexError:
            current = None
            changed = True
        super(OwnedList, self).__setitem__(index, value)
        if is_slice:
            self._populate_cache()
        else:
            if current is not None:
                key = current
            else:
                key = next((k for k, v in cache.items() if v == index), None)
            if key is not None:
                cache.replace(key, value)

        if changed:
            self._update_owner_data()

    def __delitem__(self, index):
        super(OwnedList, self).__delitem__(index)
        del self.cache[index]
        self._update_owner_data()

    def __getslice__(self, i, j):
        return self.__getitem__(slice(i, j))

    def __setslice__(self, i, j, value):
        self.__setitem__(slice(i, j), value)

    def __delslice__(self, i, j):
        self.__delitem__(slice(i, j))

    def __contains__(self, key):
        if key in self.cache:
            return True
        if len(self.cache) != len(self):
            try:
                if self.index(key) > -1:
                    return True
            except ValueError:
                pass
        return False

    def append(self, value):
        self._validate(value)
        super(OwnedList, self).append(value)
        self.cache[value] = len(self.cache) + 1
        self._update_owner_data()

    def extend(self, iterable):
        for value in iterable:
            self.append(value)

    def insert(self, index, value):
        self._validate(value)
        super(OwnedList, self).insert(index, value)
        self.cache.insert(index, value)
        self._update_owner_data()

    def remove(self, value):
        self._validate(value)
        super(OwnedList, self).remove(value)
        self.cache.pop(value, None)
        self._update_owner_data()

    def pop(self, index=-1):
        value = super(OwnedList, self).pop(index)
        self.cache.pop(value)
        self._update_owner_data()
        return value

    def index(self, value, start=None, stop=None):
        try:
            return self.cache[value]
        except (ValueError, KeyError):
            if len(self.cache) != len(self):
                self._populate_cache()
                if len(self) == len(self.cache):
                    return self.index(value)
            try:
                # Try to find matches by checking eq instead of by key
                return super().index(value)
            except ValueError:
                raise ValueError('{!r} is not in {}'.format(
                    value, self.__class__.__name__))

    def clear(self):
        del self[:]
        self.cache.clear()

    def _validate(self, value):
        raise NotImplementedError

    def _update_owner_data(self):
        if self.owner:
            owner = self.owner.with_snapshots(self.snapshots)
            owner.set_data(self.attrname, self)

    def _populate_cache(self):
        self.cache.clear()
        self.cache.update((k, i) for i, k in enumerate(self))


class FieldCollection(OwnedList):
    def _validate(self, value):
        try:
            self.field.deserialize(value, attr=self.attrname, data=self.owner)
        except ValidationError:
            return False
        return True


class ModelCollection(OwnedList):
    """
    A collection of models

    This is an mutable ordered set that can be indexed by the model's primary
    key.
    """
    model = None

    @cached_property
    def related_name(self):
        if self.owner is None:
            return None
        return self.owner._fields[self.attrname].related_name

    def __getitem__(self, key):
        try:
            return super(ModelCollection, self).__getitem__(key)
        except TypeError:
            pass
        index = self._key_to_index(key)
        try:
            return super(ModelCollection, self).__getitem__(index)
        except TypeError:
            if not isinstance(key, (int, slice)):
                raise KeyError(key)
            raise

    def __setitem__(self, key, value):
        index = self._key_to_index(key)
        current_value = self._get_index(index)
        if isinstance(index, slice):
            super(ModelCollection, self).__setitem__(
                index, (item.with_snapshots() for item in value))
        else:
            super(ModelCollection, self).__setitem__(
                index, value.with_snapshots())
        if current_value != value:
            self._clear_related(current_value)
            self._set_related(value)

    def __delitem__(self, key):
        index = self._key_to_index(key)
        current_value = self._get_index(index)
        super(ModelCollection, self).__delitem__(index)
        self._clear_related(current_value)

    def __repr__(self):
        content_repr = super(ModelCollection, self).__repr__()
        if self.owner:
            return u'{}<{}>(owner={!r}){}'.format(
                self.__class__.__name__,
                self.snapshots[0],
                self.owner,
                content_repr)
        return u'{}<{}>{}'.format(
            self.__class__.__name__,
            self.snapshots[0],
            content_repr)

    def append(self, obj):
        if obj in self:
            raise ValueError(
                u"Collection already contains object {}".format(obj))
        super(ModelCollection, self).append(obj.with_snapshots())
        self._set_related(obj)

    def add(self, obj):
        try:
            self.append(obj)
        except ValueError:
            self[obj] = obj

    def extend(self, iterable):
        for obj in iterable:
            self.append(obj)

    def update(self, iterable):
        for obj in iterable:
            self.add(obj)

    def insert(self, index, obj):
        if obj in self:
            raise ValueError(
                u"Collection already contains object {}".format(obj))
        super(ModelCollection, self).insert(index, obj.with_snapshots())
        self._set_related(obj)

    def remove(self, obj):
        super(ModelCollection, self).remove(obj)
        self._clear_related(obj)

    def discard(self, obj):
        # May still raise a ValidationError for an invalid obj
        try:
            self.remove(obj)
        except ValueError:
            pass

    def pop(self, key=unspecified):
        index = self._key_to_index(key)
        if index is unspecified:
            index = -1
        try:
            value = super(ModelCollection, self).pop(index)
        except IndexError:
            raise IndexError(u"index not in collection")
        except TypeError:
            if not isinstance(key, (int, slice)):
                raise KeyError(key)
            raise
        self._clear_related(value)
        return value

    def get(self, key, default=None):
        index = self._key_to_index(key)
        return self._get_index(index, default)

    def keys(self):
        for model in self:
            yield model.pk

    def dump(self, state='working'):
        try:
            index = ModelSnapshots.default_snapshots.index(state)
        except ValueError:
            raise ValueError(u"'{}' is not a valid state".format(state))

        context = {
            'snapshots': ModelSnapshots.default_snapshots[index:]
        }
        if self.model.opts.polymorphic:
            return [instance.__class__.file_schema(
                        context=context).dump(instance).data
                    for instance in self]
        return self.model.file_schema(
            many=True, context=context).dump(self).data

    def dumps(self, state='working'):
        return json.dumps(self.dump(state=state), sort_keys=False, indent=4,
                          separators=(', ', ': '))

    def _validate(self, value):
        validate_type(value, self.model)

    def _get_index(self, index, default=None):
        try:
            return super(ModelCollection, self).__getitem__(index)
        except (IndexError, TypeError):
            return default

    def _key_to_index(self, key):
        """
        Try to find the index at which the key resides.
        We're using index here instead of a mapping, trading efficiency for
        avoiding the added complexity of managing changes to the primary_key.

        May return an invalid index.
        """
        if not isinstance(key, slice):
            try:
                if not isinstance(key, self.model):
                    return self.index((self.model, key))
                return self.index(key)
            except ValueError:
                pass
        return key

    def _set_related(self, related):
        if related and self.owner:
            if not isinstance(related, list):
                related = [related]
            for r in (r.with_snapshots(self.snapshots) for r in related):
                set_related(r, self.related_name, self.owner)

    def _clear_related(self, related):
        if related and self.owner:
            if not isinstance(related, list):
                related = [related]
            for r in (r.with_snapshots(self.snapshots) for r in related):
                clear_related(r, self.related_name, self.owner)


class ListDescriptor(object):
    def __init__(self, attrname):
        self.attrname = attrname

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self
        try:
            collection = instance.get_data(self.attrname)
        except AttributeError:
            collection = self.new_collection(instance)
            instance.data_store.set(self.attrname, collection, 'committed')
        return collection.with_snapshots(instance.snapshots)

    def __set__(self, instance, values):
        if not isinstance(values, Sequence):
            raise ValueError(
                "You can only assign sequences to '{}'".format(self.attrname))
        collection = self.__get__(instance)
        for value in values:
            collection._validate(value)
        if collection != values:
            self.replace_collection(collection, values)

    def new_collection(self, instance):
        return FieldCollection(owner=instance, attrname=self.attrname,
                               snapshots=('committed',))

    def replace_collection(self, collection, values):
        del collection[:]
        collection.extend(values)
