import json
import os
import re
from collections import abc
from collections import deque
from random import choice
from random import randrange
from threading import Lock
from urllib.parse import quote_from_bytes

from markupsafe import escape
from markupsafe import Markup

_word_split_re = re.compile(r"(\s+)")
_lead_pattern = "|".join(map(re.escape, ("(", "<", "&lt;")))
_trail_pattern = "|".join(map(re.escape, (".", ",", ")", ">", "\n", "&gt;")))
_punctuation_re = re.compile(
    fr"^(?P<lead>(?:{_lead_pattern})*)(?P<middle>.*?)(?P<trail>(?:{_trail_pattern})*)$"
)
_simple_email_re = re.compile(r"^\S+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+$")
_striptags_re = re.compile(r"(<!--.*?-->|<[^>]*>)")
_entity_re = re.compile(r"&([^;]+);")
_letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_digits = "0123456789"

# special singleton representing missing values for the runtime
missing = type("MissingType", (), {"__repr__": lambda x: "missing"})()

# internal code
internal_code = set()

concat = "".join

_slash_escape = "\\/" not in json.dumps("/")


def contextfunction(f):
    """This decorator can be used to mark a function or method context callable.
    A context callable is passed the active :class:`Context` as first argument when
    called from the template.  This is useful if a function wants to get access
    to the context or functions provided on the context object.  For example
    a function that returns a sorted list of template variables the current
    template exports could look like this::

        @contextfunction
        def get_exported_names(context):
            return sorted(context.exported_vars)
    """
    f.contextfunction = True
    return f


def evalcontextfunction(f):
    """This decorator can be used to mark a function or method as an eval
    context callable.  This is similar to the :func:`contextfunction`
    but instead of passing the context, an evaluation context object is
    passed.  For more information about the eval context, see
    :ref:`eval-context`.

    .. versionadded:: 2.4
    """
    f.evalcontextfunction = True
    return f


def environmentfunction(f):
    """This decorator can be used to mark a function or method as environment
    callable.  This decorator works exactly like the :func:`contextfunction`
    decorator just that the first argument is the active :class:`Environment`
    and not context.
    """
    f.environmentfunction = True
    return f


def internalcode(f):
    """Marks the function as internally used"""
    internal_code.add(f.__code__)
    return f


def is_undefined(obj):
    """Check if the object passed is undefined.  This does nothing more than
    performing an instance check against :class:`Undefined` but looks nicer.
    This can be used for custom filters or tests that want to react to
    undefined variables.  For example a custom default filter can look like
    this::

        def default(var, default=''):
            if is_undefined(var):
                return default
            return var
    """
    from .runtime import Undefined

    return isinstance(obj, Undefined)


def consume(iterable):
    """Consumes an iterable without doing anything with it."""
    for _ in iterable:
        pass


def clear_caches():
    """Jinja keeps internal caches for environments and lexers.  These are
    used so that Jinja doesn't have to recreate environments and lexers all
    the time.  Normally you don't have to care about that but if you are
    measuring memory consumption you may want to clean the caches.
    """
    from .environment import _spontaneous_environments
    from .lexer import _lexer_cache

    _spontaneous_environments.clear()
    _lexer_cache.clear()


def import_string(import_name, silent=False):
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If the `silent` is True the return value will be `None` if the import
    fails.

    :return: imported object
    """
    try:
        if ":" in import_name:
            module, obj = import_name.split(":", 1)
        elif "." in import_name:
            module, _, obj = import_name.rpartition(".")
        else:
            return __import__(import_name)
        return getattr(__import__(module, None, None, [obj]), obj)
    except (ImportError, AttributeError):
        if not silent:
            raise


def open_if_exists(filename, mode="rb"):
    """Returns a file descriptor for the filename if that file exists,
    otherwise ``None``.
    """
    if not os.path.isfile(filename):
        return None

    return open(filename, mode)


def object_type_repr(obj):
    """Returns the name of the object's type.  For some recognized
    singletons the name of the object is returned instead. (For
    example for `None` and `Ellipsis`).
    """
    if obj is None:
        return "None"
    elif obj is Ellipsis:
        return "Ellipsis"

    cls = type(obj)

    if cls.__module__ == "builtins":
        return f"{cls.__name__} object"

    return f"{cls.__module__}.{cls.__name__} object"


def pformat(obj):
    """Format an object using :func:`pprint.pformat`.
    """
    from pprint import pformat

    return pformat(obj)


def urlize(text, trim_url_limit=None, rel=None, target=None):
    """Converts any URLs in text into clickable links. Works on http://,
    https:// and www. links. Links can have trailing punctuation (periods,
    commas, close-parens) and leading punctuation (opening parens) and
    it'll still do the right thing.

    If trim_url_limit is not None, the URLs in link text will be limited
    to trim_url_limit characters.

    If nofollow is True, the URLs in link text will get a rel="nofollow"
    attribute.

    If target is not None, a target attribute will be added to the link.
    """

    def trim_url(x, limit=trim_url_limit):
        if limit is not None:
            return x[:limit] + ("..." if len(x) >= limit else "")

        return x

    words = _word_split_re.split(str(escape(text)))
    rel_attr = f' rel="{escape(rel)}"' if rel else ""
    target_attr = f' target="{escape(target)}"' if target else ""

    for i, word in enumerate(words):
        match = _punctuation_re.match(word)
        if match:
            lead, middle, trail = match.groups()
            if middle.startswith("www.") or (
                "@" not in middle
                and not middle.startswith("http://")
                and not middle.startswith("https://")
                and len(middle) > 0
                and middle[0] in _letters + _digits
                and (
                    middle.endswith(".org")
                    or middle.endswith(".net")
                    or middle.endswith(".com")
                )
            ):
                middle = (
                    f'<a href="http://{middle}"{rel_attr}{target_attr}>'
                    f"{trim_url(middle)}</a>"
                )
            if middle.startswith("http://") or middle.startswith("https://"):
                middle = (
                    f'<a href="{middle}"{rel_attr}{target_attr}>{trim_url(middle)}</a>'
                )
            if (
                "@" in middle
                and not middle.startswith("www.")
                and ":" not in middle
                and _simple_email_re.match(middle)
            ):
                middle = f'<a href="mailto:{middle}">{middle}</a>'
            if lead + middle + trail != word:
                words[i] = lead + middle + trail
    return "".join(words)


def generate_lorem_ipsum(n=5, html=True, min=20, max=100):
    """Generate some lorem ipsum for the template."""
    from .constants import LOREM_IPSUM_WORDS

    words = LOREM_IPSUM_WORDS.split()
    result = []

    for _ in range(n):
        next_capitalized = True
        last_comma = last_fullstop = 0
        word = None
        last = None
        p = []

        # each paragraph contains out of 20 to 100 words.
        for idx, _ in enumerate(range(randrange(min, max))):
            while True:
                word = choice(words)
                if word != last:
                    last = word
                    break
            if next_capitalized:
                word = word.capitalize()
                next_capitalized = False
            # add commas
            if idx - randrange(3, 8) > last_comma:
                last_comma = idx
                last_fullstop += 2
                word += ","
            # add end of sentences
            if idx - randrange(10, 20) > last_fullstop:
                last_comma = last_fullstop = idx
                word += "."
                next_capitalized = True
            p.append(word)

        # ensure that the paragraph ends with a dot.
        p = " ".join(p)
        if p.endswith(","):
            p = p[:-1] + "."
        elif not p.endswith("."):
            p += "."
        result.append(p)

    if not html:
        return "\n\n".join(result)
    return Markup("\n".join(f"<p>{escape(x)}</p>" for x in result))


def url_quote(obj, charset="utf-8", for_qs=False):
    """Quote a string for use in a URL using the given charset.

    This function is misnamed, it is a wrapper around
    :func:`urllib.parse.quote`.

    :param obj: String or bytes to quote. Other types are converted to
        string then encoded to bytes using the given charset.
    :param charset: Encode text to bytes using this charset.
    :param for_qs: Quote "/" and use "+" for spaces.
    """
    if not isinstance(obj, bytes):
        if not isinstance(obj, str):
            obj = str(obj)

        obj = obj.encode(charset)

    safe = b"" if for_qs else b"/"
    rv = quote_from_bytes(obj, safe)

    if for_qs:
        rv = rv.replace("%20", "+")

    return rv


def unicode_urlencode(obj, charset="utf-8", for_qs=False):
    import warnings

    warnings.warn(
        "'unicode_urlencode' has been renamed to 'url_quote'. The old"
        " name will be removed in version 3.1.",
        DeprecationWarning,
        stacklevel=2,
    )
    return url_quote(obj, charset=charset, for_qs=for_qs)


@abc.MutableMapping.register
class LRUCache:
    """A simple LRU Cache implementation."""

    # this is fast for small capacities (something below 1000) but doesn't
    # scale.  But as long as it's only used as storage for templates this
    # won't do any harm.

    def __init__(self, capacity):
        self.capacity = capacity
        self._mapping = {}
        self._queue = deque()
        self._postinit()

    def _postinit(self):
        # alias all queue methods for faster lookup
        self._popleft = self._queue.popleft
        self._pop = self._queue.pop
        self._remove = self._queue.remove
        self._wlock = Lock()
        self._append = self._queue.append

    def __getstate__(self):
        return {
            "capacity": self.capacity,
            "_mapping": self._mapping,
            "_queue": self._queue,
        }

    def __setstate__(self, d):
        self.__dict__.update(d)
        self._postinit()

    def __getnewargs__(self):
        return (self.capacity,)

    def copy(self):
        """Return a shallow copy of the instance."""
        rv = self.__class__(self.capacity)
        rv._mapping.update(self._mapping)
        rv._queue.extend(self._queue)
        return rv

    def get(self, key, default=None):
        """Return an item from the cache dict or `default`"""
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        """Set `default` if the key is not in the cache otherwise
        leave unchanged. Return the value of this key.
        """
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def clear(self):
        """Clear the cache."""
        self._wlock.acquire()
        try:
            self._mapping.clear()
            self._queue.clear()
        finally:
            self._wlock.release()

    def __contains__(self, key):
        """Check if a key exists in this cache."""
        return key in self._mapping

    def __len__(self):
        """Return the current size of the cache."""
        return len(self._mapping)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self._mapping!r}>"

    def __getitem__(self, key):
        """Get an item from the cache. Moves the item up so that it has the
        highest priority then.

        Raise a `KeyError` if it does not exist.
        """
        self._wlock.acquire()
        try:
            rv = self._mapping[key]
            if self._queue[-1] != key:
                try:
                    self._remove(key)
                except ValueError:
                    # if something removed the key from the container
                    # when we read, ignore the ValueError that we would
                    # get otherwise.
                    pass
                self._append(key)
            return rv
        finally:
            self._wlock.release()

    def __setitem__(self, key, value):
        """Sets the value for an item. Moves the item up so that it
        has the highest priority then.
        """
        self._wlock.acquire()
        try:
            if key in self._mapping:
                self._remove(key)
            elif len(self._mapping) == self.capacity:
                del self._mapping[self._popleft()]
            self._append(key)
            self._mapping[key] = value
        finally:
            self._wlock.release()

    def __delitem__(self, key):
        """Remove an item from the cache dict.
        Raise a `KeyError` if it does not exist.
        """
        self._wlock.acquire()
        try:
            del self._mapping[key]
            try:
                self._remove(key)
            except ValueError:
                pass
        finally:
            self._wlock.release()

    def items(self):
        """Return a list of items."""
        result = [(key, self._mapping[key]) for key in list(self._queue)]
        result.reverse()
        return result

    def values(self):
        """Return a list of all values."""
        return [x[1] for x in self.items()]

    def keys(self):
        """Return a list of all keys ordered by most recent usage."""
        return list(self)

    def __iter__(self):
        return reversed(tuple(self._queue))

    def __reversed__(self):
        """Iterate over the keys in the cache dict, oldest items
        coming first.
        """
        return iter(tuple(self._queue))

    __copy__ = copy


def select_autoescape(
    enabled_extensions=("html", "htm", "xml"),
    disabled_extensions=(),
    default_for_string=True,
    default=False,
):
    """Intelligently sets the initial value of autoescaping based on the
    filename of the template.  This is the recommended way to configure
    autoescaping if you do not want to write a custom function yourself.

    If you want to enable it for all templates created from strings or
    for all templates with `.html` and `.xml` extensions::

        from jinja2 import Environment, select_autoescape
        env = Environment(autoescape=select_autoescape(
            enabled_extensions=('html', 'xml'),
            default_for_string=True,
        ))

    Example configuration to turn it on at all times except if the template
    ends with `.txt`::

        from jinja2 import Environment, select_autoescape
        env = Environment(autoescape=select_autoescape(
            disabled_extensions=('txt',),
            default_for_string=True,
            default=True,
        ))

    The `enabled_extensions` is an iterable of all the extensions that
    autoescaping should be enabled for.  Likewise `disabled_extensions` is
    a list of all templates it should be disabled for.  If a template is
    loaded from a string then the default from `default_for_string` is used.
    If nothing matches then the initial value of autoescaping is set to the
    value of `default`.

    For security reasons this function operates case insensitive.

    .. versionadded:: 2.9
    """
    enabled_patterns = tuple(f".{x.lstrip('.').lower()}" for x in enabled_extensions)
    disabled_patterns = tuple(f".{x.lstrip('.').lower()}" for x in disabled_extensions)

    def autoescape(template_name):
        if template_name is None:
            return default_for_string
        template_name = template_name.lower()
        if template_name.endswith(enabled_patterns):
            return True
        if template_name.endswith(disabled_patterns):
            return False
        return default

    return autoescape


def htmlsafe_json_dumps(obj, dumper=None, **kwargs):
    """Works exactly like :func:`dumps` but is safe for use in ``<script>``
    tags.  It accepts the same arguments and returns a JSON string.  Note that
    this is available in templates through the ``|tojson`` filter which will
    also mark the result as safe.  Due to how this function escapes certain
    characters this is safe even if used outside of ``<script>`` tags.

    The following characters are escaped in strings:

    -   ``<``
    -   ``>``
    -   ``&``
    -   ``'``

    This makes it safe to embed such strings in any place in HTML with the
    notable exception of double quoted attributes.  In that case single
    quote your attributes or HTML escape it in addition.
    """
    if dumper is None:
        dumper = json.dumps
    rv = (
        dumper(obj, **kwargs)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("'", "\\u0027")
    )
    return Markup(rv)


def convert_value_to_be_hashable(value, rec=None):
    if rec is None:
        rec = convert_value_to_be_hashable
    if isinstance(value, list) or isinstance(value, set):
        return tuple(rec(x, rec) for x in value)
    if isinstance(value, dict):
        return HashableDict([(rec(k, rec), rec(v, rec)) for (k, v) in value.items()])
    else:
        return value


class Cycler:
    """Cycle through values by yield them one at a time, then restarting
    once the end is reached. Available as ``cycler`` in templates.

    Similar to ``loop.cycle``, but can be used outside loops or across
    multiple loops. For example, render a list of folders and files in a
    list, alternating giving them "odd" and "even" classes.

    .. code-block:: html+jinja

        {% set row_class = cycler("odd", "even") %}
        <ul class="browser">
        {% for folder in folders %}
          <li class="folder {{ row_class.next() }}">{{ folder }}
        {% endfor %}
        {% for file in files %}
          <li class="file {{ row_class.next() }}">{{ file }}
        {% endfor %}
        </ul>

    :param items: Each positional argument will be yielded in the order
        given for each cycle.

    .. versionadded:: 2.1
    """

    def __init__(self, *items):
        if not items:
            raise RuntimeError("at least one item has to be provided")
        self.items = items
        self.pos = 0

    def reset(self):
        """Resets the current item to the first item."""
        self.pos = 0

    @property
    def current(self):
        """Return the current item. Equivalent to the item that will be
        returned next time :meth:`next` is called.
        """
        return self.items[self.pos]

    def next(self):
        """Return the current item, then advance :attr:`current` to the
        next item.
        """
        rv = self.current
        self.pos = (self.pos + 1) % len(self.items)
        return rv

    __next__ = next


class Joiner:
    """A joining helper for templates."""

    def __init__(self, sep=", "):
        self.sep = sep
        self.used = False

    def __call__(self):
        if not self.used:
            self.used = True
            return ""
        return self.sep


class Namespace:
    """A namespace object that can hold arbitrary attributes.  It may be
    initialized from a dictionary or with keyword arguments."""

    def __init__(*args, **kwargs):  # noqa: B902
        self, args = args[0], args[1:]
        self.__attrs = dict(*args, **kwargs)

    def __getattribute__(self, name):
        # __class__ is needed for the awaitable check in async mode
        if name in {"_Namespace__attrs", "__class__"}:
            return object.__getattribute__(self, name)
        try:
            return self.__attrs[name]
        except KeyError:
            raise AttributeError(name)

    def __setitem__(self, name, value):
        self.__attrs[name] = value

    def __repr__(self):
        return f"<Namespace {self.__attrs!r}>"


class HashableDict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.items())))


# does this python version support async for in and async generators?
try:
    exec("async def _():\n async for _ in ():\n  yield _")
    have_async_gen = True
except SyntaxError:
    have_async_gen = False
