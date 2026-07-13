# PSerialization Adversarial Code Review

**Repository:** `SteffenCucos/PSerialization`  
**Reviewed branch:** `main`  
**Reviewed commit:** `1e9b0c5206b81b20f6f9ff403ac5f98687ba1a6d`  
**Review type:** Adversarial correctness, safety, API-contract, packaging, and test-coverage review

## Executive summary

PSerialization is a compact and understandable prototype that handles its demonstrated happy paths, including nested objects, collections, enums, unions, literals, type variables, middleware, and cycle detection.

The current deserialization architecture is not safe enough for untrusted input or for use as a general-purpose typed deserializer. The principal problem is that it combines:

1. permissive coercion;
2. constructor bypass;
3. direct mutation of object internals;
4. acceptance of unknown fields;
5. weak enforcement of missing and nullable fields.

As a result, a successful call to `deserialize()` does **not** establish that the returned object satisfies its declared types, constructor invariants, dataclass requirements, or intended security boundaries.

The following findings should be treated as release blockers:

- constructors and `__post_init__` are bypassed;
- unknown input keys are mass-assigned by default;
- `None` is accepted for non-nullable targets;
- optional unions with more than one non-`None` branch are handled incorrectly;
- collection subclasses can silently serialize to the wrong representation;
- missing required fields are assigned `None` rather than rejected.

## Scope

Primary files reviewed:

- `src/pserialize/serialize.py`
- `src/pserialize/deserialize.py`
- `src/pserialize/deserialize_impl.py`
- `src/pserialize/serialization_utils.py`
- `src/pserialize/__init__.py`
- `src/pserialize/middleware/datetime.py`
- `README.md`
- `setup.cfg`
- `pyproject.toml`
- `.github/workflows/push_workflow.yml`
- `.github/workflows/publish.yml`
- tests under `tests/`

## Severity summary

| ID | Severity | Finding |
|---|---|---|
| F-01 | Critical | Deserialization bypasses constructors and object invariants |
| F-02 | Critical | Unknown fields are mass-assigned by default |
| F-03 | High | `None` is accepted for every target type |
| F-04 | High | Optional unions discard valid branches |
| F-05 | High | Missing required fields are silently assigned `None` |
| F-06 | High | Collection subclasses can silently lose contents |
| F-07 | High | Primitive coercion is lossy and surprising |
| F-08 | Medium | Union handling suppresses arbitrary implementation errors |
| F-09 | Medium | Middleware type contract and README examples are inconsistent with runtime behavior |
| F-10 | Medium | Raw collection targets are unsupported or misrouted |
| F-11 | Medium | Serialization exposes private and sensitive object state |
| F-12 | Medium | Serialized dictionary keys can become unhashable or non-JSON-compatible |
| F-13 | Medium | `serialize_into()` has contradictory return semantics and drops middleware |
| F-14 | Medium | Error messages can leak sensitive input values |
| F-15 | Medium | `strict` is misleading and does not provide strict validation |
| F-16 | Medium | README imports reference modules that do not exist |
| F-17 | Medium | License metadata contradicts the repository documentation |
| F-18 | Medium | Publishing can release a version inconsistent with its Git tag |
| F-19 | Medium | Push CI does not validate the installed package or supported Python range |
| F-20 | Low | Built-in datetime middleware uses mutable default arguments |

---

## F-01: Deserialization bypasses constructors and object invariants

**Severity:** Critical  
**Location:** `src/pserialize/deserialize_impl.py`, `__deserialize_simple_object()`

### Problem

The implementation allocates objects with `object.__new__(classType)` and then writes directly into `cls.__dict__`.

This bypasses:

- `classType.__init__()`;
- dataclass-generated `__init__()`;
- dataclass `__post_init__()`;
- validation and normalization logic;
- derived-field construction;
- side effects required for a valid instance;
- frozen-dataclass protections;
- descriptors and property setters.

It also fails for classes that do not expose `__dict__`, such as many `__slots__` classes and slots dataclasses.

### Example

```python
from pserialize import deserialize

class Account:
    balance: int

    def __init__(self, balance: int):
        if balance < 0:
            raise ValueError("balance cannot be negative")
        self.balance = balance
        self.is_overdrawn = balance == 0

account = deserialize({"balance": -100}, Account)

# Current behavior can produce an Account that normal construction rejects.
assert account.balance == -100
assert not hasattr(account, "is_overdrawn")
```

A dataclass example:

```python
from dataclasses import dataclass, field
from pserialize import deserialize

@dataclass
class Order:
    quantity: int
    unit_price: float
    total: float = field(init=False)

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        self.total = self.quantity * self.unit_price

order = deserialize({"quantity": -1, "unit_price": 10.0}, Order)

# Constructor validation and total calculation are bypassed.
```

### Impact

- Invalid domain objects can enter the application.
- Security or authorization invariants implemented in constructors can be bypassed.
- Objects can be only partially initialized.
- Behavior differs substantially from normal Python construction.
- Equality may make broken instances appear valid in simple tests.

### Suggested fix

Deserialize input fields into constructor arguments, then invoke the target constructor:

```python
kwargs = deserialize_fields(data, schema)
return class_type(**kwargs)
```

For dataclasses:

- use `dataclasses.fields(class_type)`;
- honor `init=False`;
- honor `default` and `default_factory`;
- reject missing required `init=True` fields;
- allow the generated constructor to invoke `__post_init__`.

For ordinary classes:

- inspect `inspect.signature(class_type)` or `class_type.__init__`;
- map declared constructor parameters;
- call `class_type(**kwargs)`.

If constructor bypass is retained for specialized use cases, expose it explicitly as an unsafe mode, for example:

```python
deserialize(data, Target, construction="unsafe_allocate")
```

It should never be the default.

### Suggested tests

```python
def test_deserialize_calls_constructor():
    calls = []

    class Model:
        value: int

        def __init__(self, value: int):
            calls.append(value)
            self.value = value

    result = deserialize({"value": 3}, Model)

    assert result.value == 3
    assert calls == [3]
```

```python
def test_constructor_validation_is_enforced():
    class Account:
        balance: int

        def __init__(self, balance: int):
            if balance < 0:
                raise ValueError("negative")
            self.balance = balance

    with pytest.raises(DeserializeClassException):
        deserialize({"balance": -1}, Account)
```

```python
def test_dataclass_post_init_runs():
    @dataclass
    class Model:
        value: int
        doubled: int = field(init=False)

        def __post_init__(self):
            self.doubled = self.value * 2

    assert deserialize({"value": 4}, Model).doubled == 8
```

```python
def test_slots_dataclass_is_supported():
    @dataclass(slots=True)
    class Model:
        value: int

    assert deserialize({"value": 4}, Model) == Model(4)
```

---

## F-02: Unknown fields are mass-assigned by default

**Severity:** Critical  
**Location:** `src/pserialize/deserialize_impl.py`, `__deserialize_simple_object()`

### Problem

When `strict=False`, the default, an unknown input key receives no field type and is assigned directly to the object's `__dict__`.

This is a mass-assignment vulnerability pattern. Input data can create undeclared internal flags and shadow instance attributes.

### Example

```python
from dataclasses import dataclass
from pserialize import deserialize

@dataclass
class User:
    name: str

user = deserialize(
    {
        "name": "Alice",
        "is_admin": True,
        "_authenticated": True,
        "account_status": "verified",
    },
    User,
)

assert user.is_admin is True
assert user._authenticated is True
```

### Impact

- Untrusted payloads can introduce security-sensitive attributes.
- Internal state can be forged.
- Typos in payload keys are silently accepted.
- API schema drift is hidden instead of detected.

### Suggested fix

Reject unknown fields by default. Replace the boolean `strict` option with an explicit policy:

```python
deserialize(data, User, unknown_fields="reject")
deserialize(data, User, unknown_fields="ignore")
deserialize(data, User, unknown_fields="preserve")
```

Recommended default: `"reject"`.

If preserving unknown fields remains supported, restrict it to target types that explicitly opt in.

### Suggested tests

```python
def test_unknown_fields_are_rejected_by_default():
    @dataclass
    class User:
        name: str

    with pytest.raises(UnknownFieldError):
        deserialize({"name": "Alice", "is_admin": True}, User)
```

```python
def test_unknown_fields_can_be_explicitly_ignored():
    @dataclass
    class User:
        name: str

    user = deserialize(
        {"name": "Alice", "extra": 1},
        User,
        unknown_fields="ignore",
    )

    assert user == User("Alice")
    assert not hasattr(user, "extra")
```

---

## F-03: `None` is accepted for every target type

**Severity:** High  
**Location:** `src/pserialize/deserialize_impl.py`, `__deserialize_inner()`

### Problem

The implementation returns `None` immediately when the input is `None`, before checking whether the target type allows nullability.

### Example

```python
assert deserialize(None, int) is None
assert deserialize(None, str) is None
assert deserialize(None, list[int]) is None
assert deserialize(None, RequiredDomainObject) is None
```

All of these contradict the requested target type.

### Impact

- Non-nullable annotations are not enforced.
- Required object fields can become `None`.
- Downstream code fails later and farther from the actual input error.

### Suggested fix

Accept `None` only for:

- `Any`;
- `NoneType`;
- a union containing `NoneType`.

Otherwise raise a typed mismatch error containing the field path.

### Suggested tests

```python
@pytest.mark.parametrize("target", [int, str, float, bool, list[int], dict[str, int]])
def test_none_is_rejected_for_non_optional_targets(target):
    with pytest.raises(DeserializeClassException):
        deserialize(None, target)
```

```python
def test_none_is_accepted_for_optional_target():
    assert deserialize(None, int | None) is None
```

---

## F-04: Optional unions discard valid branches

**Severity:** High  
**Location:** `src/pserialize/deserialize_impl.py`, optional handling in `__deserialize_inner()`

### Problem

When a union contains `NoneType`, the implementation selects the first non-`None` argument and deserializes exclusively as that type.

For a type such as `int | str | None`, the `str` branch may never be attempted.

### Example

```python
from dataclasses import dataclass

@dataclass
class Payload:
    value: int | str | None

result = deserialize({"value": "hello"}, Payload)

# Expected: Payload(value="hello")
# Current behavior: attempts int("hello") and fails.
```

Union ordering also changes coercion behavior:

```python
@dataclass
class A:
    value: int | str | None

@dataclass
class B:
    value: str | int | None

# The same input may produce different types solely due to branch order.
```

### Suggested fix

Remove the special optional branch. Treat optional values as ordinary unions:

1. if the value is `None`, match `NoneType` exactly;
2. prefer a branch whose runtime type already matches;
3. otherwise attempt allowed coercions across all non-`None` branches;
4. report all branch failures if no branch succeeds.

### Suggested tests

```python
def test_optional_union_tries_all_non_none_branches():
    assert deserialize("hello", int | str | None) == "hello"
```

```python
def test_optional_union_preserves_existing_runtime_type():
    assert deserialize(4, str | int | None) == 4
```

```python
def test_optional_union_accepts_none():
    assert deserialize(None, int | str | None) is None
```

---

## F-05: Missing required fields are silently assigned `None`

**Severity:** High  
**Location:** `src/pserialize/deserialize_impl.py`, `__deserialize_simple_object()`

### Problem

After processing supplied input fields, every remaining annotation or constructor hint is assigned `None`.

This ignores:

- whether the field is required;
- whether it is nullable;
- dataclass defaults;
- dataclass default factories;
- constructor defaults.

### Example

```python
from dataclasses import dataclass, field

@dataclass
class User:
    id: int
    name: str
    tags: list[str] = field(default_factory=list)

user = deserialize({"id": 1}, User)

# Current behavior:
assert user.name is None
assert user.tags is None
```

### Impact

- Required-field validation is defeated.
- Default values and factories are discarded.
- Returned objects violate their declared schema.
- Missing data becomes indistinguishable from explicit null data.

### Suggested fix

For every target field:

1. use the input value when present;
2. otherwise use its declared default;
3. otherwise call its `default_factory`;
4. otherwise reject the payload as missing a required field.

Do not synthesize `None` unless `None` is an actual declared default.

### Suggested tests

```python
def test_missing_required_field_is_rejected():
    @dataclass
    class User:
        id: int
        name: str

    with pytest.raises(MissingFieldError):
        deserialize({"id": 1}, User)
```

```python
def test_dataclass_default_is_preserved():
    @dataclass
    class User:
        name: str = "anonymous"

    assert deserialize({}, User) == User(name="anonymous")
```

```python
def test_default_factory_is_called():
    @dataclass
    class User:
        tags: list[str] = field(default_factory=list)

    first = deserialize({}, User)
    second = deserialize({}, User)

    assert first.tags == []
    assert first.tags is not second.tags
```

---

## F-06: Collection subclasses can silently lose contents

**Severity:** High  
**Location:** `src/pserialize/serialize.py`, `_serialize_inner()`

### Problem

Serialization dispatch uses exact type equality for built-in collections:

```python
if class_type in (list, tuple, set, frozenset):
    ...
if class_type is dict:
    ...
```

A subclass of `list`, `dict`, `tuple`, or another collection falls through to basic-object serialization using `vars()`.

### Example

```python
class IDs(list):
    pass

value = IDs([1, 2, 3])
serialized = serialize(value)

# A list subclass can serialize as {}, silently dropping all elements.
```

This can also affect custom mappings, `defaultdict`, `OrderedDict`, named tuples, and domain-specific collection wrappers.

### Impact

- Silent data loss.
- Runtime behavior depends on exact concrete type rather than collection semantics.
- Extending a built-in collection changes wire representation unexpectedly.

### Suggested fix

Use deliberate protocol-based dispatch, ordered from specific to general:

```python
if isinstance(value, Mapping):
    ...
elif isinstance(value, tuple) and hasattr(value, "_fields"):
    ...
elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
    ...
elif isinstance(value, Set):
    ...
```

Alternatively, reject unsupported subclasses explicitly rather than serializing them incorrectly.

### Suggested tests

```python
def test_list_subclass_preserves_elements():
    class IDs(list):
        pass

    assert serialize(IDs([1, 2, 3])) == [1, 2, 3]
```

```python
def test_dict_subclass_preserves_entries():
    class Attributes(dict):
        pass

    assert serialize(Attributes(name="Alice")) == {"name": "Alice"}
```

---

## F-07: Primitive coercion is lossy and surprising

**Severity:** High  
**Location:** `src/pserialize/deserialize_impl.py`, primitive deserialization

### Problem

Primitive conversion delegates directly to the target constructor:

```python
return class_type(value)
```

This creates Python-specific coercions that are often inappropriate for typed validation.

### Examples

```python
assert deserialize("false", bool) is True
assert deserialize("0", bool) is True
assert deserialize(4.9, int) == 4
assert deserialize(True, int) == 1
assert deserialize(0, str) == "0"
```

`bool("false")` is `True` because all non-empty strings are truthy. `int(4.9)` silently truncates fractional data.

### Impact

- Input meaning can change silently.
- Invalid payloads appear valid.
- Numeric precision can be lost.
- Boolean configuration values can be interpreted opposite to user intent.

### Suggested fix

Separate validation and coercion:

```python
deserialize(value, Target, coerce=False)  # recommended default
deserialize(value, Target, coerce=True)
```

Under strict validation:

- `int` accepts integers but should normally reject `bool`;
- `float` accepts integers and floats, subject to explicit policy;
- `str` accepts strings only;
- `bool` accepts booleans only.

Under coercion mode, define a finite set of safe conversions. For boolean strings, accept only an explicit vocabulary such as:

- true: `"true"`, `"1"`, `"yes"`, `"on"`;
- false: `"false"`, `"0"`, `"no"`, `"off"`.

Reject lossy float-to-int conversions unless the float is integral.

### Suggested tests

```python
def test_false_string_does_not_become_true():
    with pytest.raises(TypeMismatchError):
        deserialize("false", bool)
```

```python
def test_explicit_boolean_coercion():
    assert deserialize("false", bool, coerce=True) is False
    assert deserialize("true", bool, coerce=True) is True
```

```python
def test_fractional_float_is_not_silently_truncated():
    with pytest.raises(TypeMismatchError):
        deserialize(4.9, int, coerce=True)
```

---

## F-08: Union handling suppresses arbitrary implementation errors

**Severity:** Medium  
**Location:** `src/pserialize/deserialize_impl.py`, `__deserialize_union()`

### Problem

Every `Exception` from a union branch is caught and ignored before the next branch is attempted.

This suppresses more than expected type mismatch errors. It can hide:

- bugs in middleware;
- `AttributeError` caused by broken implementation code;
- unexpected runtime failures;
- programmer errors in constructors;
- resource or logic failures unrelated to branch compatibility.

### Example

```python
class Exploding:
    pass

middleware = {
    Exploding: lambda value, context: 1 / 0,
}

# In a union, ZeroDivisionError may be swallowed and another branch selected.
result = deserialize("5", Exploding | int, middleware=middleware)
```

### Impact

- Real defects can be disguised as successful deserialization.
- Debugging becomes difficult.
- Branch selection can depend on unrelated bugs.

### Suggested fix

Catch only expected deserialization mismatch exceptions:

```python
except DeserializationMismatch as error:
    branch_errors.append(error)
```

Allow unexpected exceptions to propagate. When all branches fail, raise a structured union error containing the failure for each branch.

### Suggested tests

```python
def test_union_does_not_swallow_unexpected_middleware_error():
    def broken(value, context):
        raise RuntimeError("middleware bug")

    with pytest.raises(RuntimeError, match="middleware bug"):
        deserialize("1", Custom | int, middleware={Custom: broken})
```

---

## F-09: Middleware contract is inconsistent with runtime behavior

**Severity:** Medium  
**Locations:**

- `src/pserialize/serialize.py`
- `src/pserialize/deserialize_impl.py`
- `src/pserialize/__init__.py`
- `README.md`

### Problem

Middleware is annotated as a one-argument callable:

```python
Callable[[object], type]
```

At runtime, it is called with two arguments:

```python
serializer(value, middleware)
deserializer(value, middleware)
```

The README demonstrates one-argument functions, which fail when copied.

The return type annotation `type` is also inaccurate: middleware returns a serialized or deserialized value, not a class object.

### Example

```python
def serialize_datetime(value: datetime):
    return value.isoformat()

serializer = Serializer(middleware={datetime: serialize_datetime})
serializer.serialize(datetime.now())

# TypeError: serialize_datetime() takes 1 positional argument but 2 were given
```

### Suggested fix

Define explicit protocols and a context object:

```python
from typing import Any, Protocol

class SerializationContext(Protocol):
    def serialize(self, value: Any) -> JsonValue: ...

class SerializerMiddleware(Protocol):
    def __call__(self, value: Any, context: SerializationContext) -> JsonValue: ...
```

The context should preserve:

- recursive middleware application;
- cycle-detection state;
- field path;
- configuration options.

Do the same for deserialization.

### Suggested tests

```python
def test_readme_style_middleware_contract_matches_runtime():
    def serializer(value, context):
        return value.isoformat()

    result = Serializer({datetime: serializer}).serialize(TEST_DATETIME)
    assert result == TEST_DATETIME.isoformat()
```

Add a static type-check job using mypy or pyright so callable-arity mismatches are detected before release.

---

## F-10: Raw collection targets are unsupported or misrouted

**Severity:** Medium  
**Location:** `src/pserialize/deserialize_impl.py`, collection dispatch

### Problem

Collection deserialization only checks `get_origin(class_type)`. Raw built-ins such as `list`, `dict`, `tuple`, `set`, and `frozenset` have no generic origin and fall through to simple-object construction.

### Example

```python
deserialize([1, 2, 3], list)
deserialize({"a": 1}, dict)
deserialize([1, 2], tuple)
```

These should either return the corresponding raw collection or fail with a clear unsupported-target error. They should not be treated as ordinary classes.

### Suggested fix

Support both parameterized and raw collection targets:

```python
origin = get_origin(target) or target

if origin is list:
    item_type = get_args(target)[0] if get_args(target) else Any
```

Validate that the input itself has the expected collection shape before iterating it.

### Suggested tests

```python
@pytest.mark.parametrize(
    ("value", "target", "expected"),
    [
        ([1, 2], list, [1, 2]),
        ({"a": 1}, dict, {"a": 1}),
        ([1, 2], tuple, (1, 2)),
        ([1, 2], set, {1, 2}),
        ([1, 2], frozenset, frozenset({1, 2})),
    ],
)
def test_raw_collection_targets(value, target, expected):
    assert deserialize(value, target) == expected
```

---

## F-11: Serialization exposes private and sensitive object state

**Severity:** Medium  
**Location:** `src/pserialize/serialize.py`, `__serialize_basic_object()`

### Problem

All entries returned by `vars(object)` are serialized. This includes:

- private attributes;
- password hashes;
- access tokens;
- caches;
- internal state flags;
- ORM bookkeeping;
- implementation details not intended for the wire format.

### Example

```python
class Session:
    def __init__(self):
        self.user_id = 10
        self._access_token = "secret-token"
        self._cache = {"sensitive": "value"}

assert serialize(Session()) == {
    "user_id": 10,
    "_access_token": "secret-token",
    "_cache": {"sensitive": "value"},
}
```

### Impact

- Accidental disclosure of secrets and personal information.
- Tight coupling between wire format and implementation details.
- Internal refactors become breaking serialization changes.

### Suggested fix

Adopt allowlist-based field selection. Options include:

- dataclass fields only;
- constructor parameters only;
- explicit class configuration;
- dataclass metadata such as `metadata={"serialize": False}`;
- field aliases and exclusion sets.

For example:

```python
@dataclass
class Session:
    user_id: int
    access_token: str = field(metadata={"serialize": False})
```

Private names should be excluded by default unless explicitly enabled.

### Suggested tests

```python
def test_private_fields_are_not_serialized_by_default():
    class Model:
        def __init__(self):
            self.public = 1
            self._private = 2

    assert serialize(Model()) == {"public": 1}
```

```python
def test_explicit_field_exclusion():
    @dataclass
    class Credentials:
        username: str
        password: str = field(metadata={"serialize": False})

    assert serialize(Credentials("alice", "secret")) == {"username": "alice"}
```

---

## F-12: Serialized dictionary keys can become unhashable or non-JSON-compatible

**Severity:** Medium  
**Location:** `src/pserialize/serialize.py`, `__serialize_dict()`

### Problem

Dictionary keys are recursively serialized and immediately used as keys in the output dictionary.

A hashable source key can serialize to an unhashable value.

### Example

```python
serialize({(1, 2): "value"})

# The tuple serializes to [1, 2].
# The list cannot be used as a dictionary key.
# TypeError: unhashable type: 'list'
```

Even when keys remain hashable, JSON object keys are constrained to strings by most consumers.

### Suggested fix

Define a clear mapping-key policy:

1. **JSON mode:** require string keys and reject all others;
2. **coercion mode:** convert supported scalar keys to strings with collision checks;
3. **general mode:** serialize mappings as a list of key/value pairs:

```json
{"$mapping": [[serialized_key, serialized_value]]}
```

Never silently overwrite colliding keys after coercion.

### Suggested tests

```python
def test_tuple_dictionary_key_has_explicit_behavior():
    with pytest.raises(UnsupportedKeyTypeError):
        serialize({(1, 2): "value"})
```

```python
def test_key_coercion_detects_collisions():
    with pytest.raises(KeyCollisionError):
        serialize({1: "int", "1": "str"}, key_policy="stringify")
```

---

## F-13: `serialize_into()` has contradictory semantics and drops middleware

**Severity:** Medium  
**Location:** `src/pserialize/serialize.py`, `serialize_into()`

### Problem

The docstring states that the function returns an instance of `c_type`, but it actually serializes the converted object and returns a primitive representation.

It also invokes the final `serialize(custom_type)` without passing `s_middleware`.

### Example

```python
result = serialize_into(user, UserDTO)

# Documentation implies UserDTO.
# Tests expect dict.
```

Middleware loss example:

```python
@dataclass
class Source:
    created_at: datetime

@dataclass
class Target:
    created_at: datetime

result = serialize_into(
    Source(datetime.now()),
    Target,
    s_middleware={datetime: datetime_serializer},
    d_middleware={datetime: datetime_deserializer},
)

# The final serialize() call no longer receives datetime middleware.
```

### Suggested fix

Split the function into two clear APIs:

```python
convert(value, target_type) -> target_type
serialize_as(value, schema_type) -> JsonValue
```

If `serialize_into()` is retained, define and document one return type and consistently pass middleware through the full operation.

### Suggested tests

```python
def test_convert_returns_target_instance():
    assert isinstance(convert(source, Target), Target)
```

```python
def test_serialize_as_preserves_middleware():
    result = serialize_as(source, Target, middleware={datetime: serializer})
    assert result["created_at"] == source.created_at.isoformat()
```

---

## F-14: Error messages can leak sensitive input values

**Severity:** Medium  
**Location:** `src/pserialize/deserialize_impl.py`, exception `__repr__()` methods

### Problem

Deserialization exceptions embed the raw failing input value in their string representation.

### Example

```python
try:
    deserialize({"api_token": "super-secret-token"}, TokenPayload)
except Exception as error:
    logger.exception("Invalid request: %s", error)
```

The raw token may be copied into application logs, telemetry, support systems, and error reports.

### Suggested fix

Use structured exceptions with fields such as:

- `path`;
- `expected_type`;
- `error_code`;
- `cause`;
- optional redacted preview.

Do not include raw values in `str(error)` by default. Provide an explicit debugging option for safe environments.

### Suggested tests

```python
def test_error_message_does_not_include_raw_secret():
    secret = "super-secret-token"

    with pytest.raises(DeserializationError) as captured:
        deserialize(secret, int)

    assert secret not in str(captured.value)
```

---

## F-15: `strict` is misleading and does not provide strict validation

**Severity:** Medium

### Problem

`strict=True` only skips unknown fields. It does not:

- reject unknown fields;
- reject missing fields;
- reject `None` for non-optional targets;
- disable primitive coercion;
- enforce constructor invariants;
- require exact runtime types.

This is materially different from what users generally expect from a strict deserialization mode.

### Suggested fix

Replace the overloaded boolean with explicit options:

```python
DeserializationOptions(
    unknown_fields="reject",
    missing_fields="reject",
    coerce=False,
    construct="constructor",
    allow_none_only_when_declared=True,
)
```

A `strict=True` convenience option may map to a documented preset of those settings.

### Suggested tests

Add one test for every guarantee promised by strict mode. Avoid a single test that only verifies unknown-field omission.

---

## F-16: README imports reference modules that do not exist

**Severity:** Medium  
**Location:** `README.md`

### Problem

The README imports:

```python
from pserialize.serializer import Serializer
from pserialize.deserializer import Deserializer
```

The repository defines these classes in `pserialize.__init__` and does not contain matching `serializer.py` and `deserializer.py` public modules.

### Impact

- First-use examples fail.
- Users cannot determine the supported public import path.
- Documentation tests would fail if they existed.

### Suggested fix

Either update examples to:

```python
from pserialize import Serializer, Deserializer
```

or add stable compatibility modules that re-export those classes.

### Suggested tests

Run README code blocks as part of CI using doctest, pytest-markdown, or a small documentation smoke test.

```python
def test_public_readme_imports():
    from pserialize import Serializer, Deserializer

    assert Serializer is not None
    assert Deserializer is not None
```

---

## F-17: License metadata contradicts repository documentation

**Severity:** Medium  
**Locations:** `setup.cfg`, `README.md`

### Problem

`setup.cfg` declares the MIT license classifier, while the README says no license has been selected. No clear committed license grant is presented.

### Impact

- Package consumers do not have unambiguous permission to copy, modify, or distribute the code.
- Published metadata may be inaccurate.

### Suggested fix

Choose a license and commit the full license text as `LICENSE`. Then make all package metadata and documentation consistent.

If no license is intended, remove the MIT classifier and avoid public package publication until licensing is resolved.

### Suggested tests/checks

Add a release check that confirms:

- `LICENSE` exists;
- the declared classifier matches the license file;
- package metadata contains the selected license information.

---

## F-18: Publishing can release a version inconsistent with its Git tag

**Severity:** Medium  
**Locations:** `.github/workflows/publish.yml`, `setup.cfg`

### Problem

Every tag matching `v*` triggers package publication, while the package version is independently hardcoded in `setup.cfg`.

A tag such as `v0.0.7` can build a package still reporting version `0.0.6`.

### Impact

- Releases can fail because a version already exists on PyPI.
- Git release history and package metadata can diverge.
- Users cannot reliably map a package version to source code.

### Suggested fix

Use one source of truth:

- derive package version from Git tags using `setuptools-scm`; or
- add a workflow step that compares the tag to the built package version and fails on mismatch.

Example validation:

```bash
TAG_VERSION="${GITHUB_REF_NAME#v}"
PACKAGE_VERSION="$(python -c 'import importlib.metadata; print(importlib.metadata.version("pserialization"))')"
test "$TAG_VERSION" = "$PACKAGE_VERSION"
```

### Suggested tests/checks

- Test a matching version/tag case.
- Test a mismatched version/tag case.
- Build the wheel and inspect its metadata before publishing.

---

## F-19: Push CI does not validate the installed package or supported Python range

**Severity:** Medium  
**Location:** `.github/workflows/push_workflow.yml`

### Problem

The push workflow:

- runs only on pushes, not pull requests;
- tests only Python 3.9;
- does not install the package before running tests;
- allows most lint findings to exit successfully;
- permits tests to import through `src.pserialize`, which validates repository layout rather than the installed public package.

The publish workflow uses Python 3.11, so the ordinary CI and release CI validate different environments.

### Impact

- Broken packaging can pass tests.
- Public imports can fail while internal `src.*` imports pass.
- Newer Python syntax and typing behavior are not tested across the supported range.
- Pull requests can merge without CI coverage.

### Suggested fix

Use a matrix for all supported versions and install the package:

```yaml
on:
  push:
  pull_request:

strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11", "3.12", "3.13"]

steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python-version }}
  - run: python -m pip install -e .
  - run: python -m pip install pytest
  - run: pytest
```

Tests should import only from the installed public package:

```python
from pserialize import serialize, deserialize, Serializer, Deserializer
```

Add separate jobs for:

- formatting/linting;
- static typing;
- build and `twine check`;
- wheel installation smoke test.

### Suggested tests/checks

```bash
python -m build
python -m pip install --force-reinstall dist/*.whl
python -c "from pserialize import Serializer, Deserializer"
pytest
```

---

## F-20: Built-in datetime middleware uses mutable default arguments

**Severity:** Low  
**Location:** `src/pserialize/middleware/datetime.py`

### Problem

Both middleware methods use `{}` as a default argument:

```python
def serializer(obj, middleware={}):
    ...
```

The current methods do not mutate the dictionary, so this is not presently exploitable, but it is a fragile API pattern and contradicts the package-level effort to avoid shared mutable defaults.

### Suggested fix

Use `None`:

```python
def serializer(obj: datetime, context=None) -> str:
    return obj.isoformat()
```

Prefer the same context protocol used by all other middleware.

### Suggested test

Static linting with Ruff rule `B006` can prevent mutable default arguments.

---

# Additional test gaps

The existing suite covers many nominal round trips but does not sufficiently probe malformed shapes, invariants, security boundaries, and unsupported objects.

## Container input-shape tests

```python
@pytest.mark.parametrize(
    ("value", "target"),
    [
        ("not-a-list", list[int]),
        ({"a": 1}, list[int]),
        ([1, 2], dict[str, int]),
        (123, tuple[int, ...]),
    ],
)
def test_container_target_rejects_wrong_input_shape(value, target):
    with pytest.raises(TypeMismatchError):
        deserialize(value, target)
```

## Frozen dataclass tests

```python
def test_frozen_dataclass_uses_normal_construction():
    @dataclass(frozen=True)
    class Frozen:
        value: int

    assert deserialize({"value": 1}, Frozen) == Frozen(1)
```

## Descriptor/property tests

```python
def test_deserializer_does_not_write_arbitrary_descriptor_state():
    class Model:
        def __init__(self, value: int):
            self.value = value

        @property
        def doubled(self):
            return self.value * 2

    with pytest.raises(UnknownFieldError):
        deserialize({"value": 1, "doubled": 100}, Model)
```

## Inheritance-aware middleware tests

The current middleware lookup is based on exact types. The intended behavior for subclasses should be documented and tested.

```python
def test_middleware_subclass_policy_is_explicit():
    class Identifier(str):
        pass

    # Decide whether str middleware applies to Identifier.
    # Whichever behavior is selected must be stable and documented.
```

## Recursive middleware and cycle-state tests

Middleware receives the raw middleware mapping rather than a recursive serialization context, which encourages middleware authors to call top-level `serialize()` and reset cycle state.

```python
def test_recursive_middleware_preserves_cycle_detection_context():
    class Wrapper:
        def __init__(self, value):
            self.value = value

    wrapper = Wrapper(None)
    wrapper.value = wrapper

    with pytest.raises(SerializeCycleException):
        serialize(wrapper, middleware={Wrapper: wrapper_serializer})
```

## Error-path tests

Test structured paths instead of brittle full exception strings:

```python
def test_nested_error_contains_structured_path():
    with pytest.raises(DeserializationError) as captured:
        deserialize(payload, Parent)

    assert captured.value.path == ("children", 1, "count")
    assert captured.value.expected_type is int
```

## Property-based tests

Hypothesis would be valuable for serializer invariants:

```python
@given(st.integers())
def test_integer_round_trip(value):
    assert deserialize(serialize(value), int) == value
```

Recommended generated domains:

- nested JSON-compatible structures;
- fixed and variadic tuples;
- sets and frozensets;
- enums;
- unions with overlapping coercions;
- dataclasses with defaults and factories;
- malformed container shapes;
- deeply nested values;
- shared references and cycles.

# Recommended architecture

## 1. Define the serialized value domain

Introduce a recursive alias representing supported wire values:

```python
from typing import TypeAlias

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
```

If non-JSON mappings are supported, define a separate representation rather than weakening the JSON contract.

## 2. Separate schema inspection from execution

Build a schema adapter for each target type:

- primitive adapter;
- enum adapter;
- literal adapter;
- union adapter;
- list/tuple/set/mapping adapter;
- dataclass adapter;
- ordinary constructor adapter;
- middleware adapter.

Cache adapters where safe to avoid repeatedly calling reflection APIs.

## 3. Introduce explicit contexts

```python
@dataclass
class DeserializationContext:
    options: DeserializationOptions
    path: tuple[str | int, ...]
    middleware: MiddlewareRegistry

    def child(self, segment: str | int) -> "DeserializationContext": ...
    def deserialize(self, value: Any, target: Any) -> Any: ...
```

This centralizes recursion, path tracking, options, middleware, and error generation.

## 4. Separate mismatch errors from implementation errors

Use a dedicated hierarchy:

```python
class SerializationError(Exception): ...
class DeserializationError(Exception): ...
class TypeMismatchError(DeserializationError): ...
class MissingFieldError(DeserializationError): ...
class UnknownFieldError(DeserializationError): ...
class UnionMismatchError(DeserializationError): ...
```

Only mismatch errors should be consumed while exploring union branches.

## 5. Make policies explicit

Suggested options:

```python
@dataclass(frozen=True)
class DeserializationOptions:
    coerce: bool = False
    unknown_fields: Literal["reject", "ignore"] = "reject"
    missing_fields: Literal["reject", "use_none"] = "reject"
    construct: Literal["constructor", "unsafe_allocate"] = "constructor"
```

Avoid adding further ambiguous booleans.

# Recommended implementation sequence

## Phase 1: Correctness and safety

1. Reject `None` for non-nullable targets.
2. Fix optional union handling.
3. Reject unknown fields by default.
4. Respect required fields, defaults, and factories.
5. Construct objects through their constructors.
6. Validate collection input shapes.
7. Split strict validation from coercion.

## Phase 2: API stabilization

1. Define middleware protocols and contexts.
2. Define the serialized value domain.
3. Split or rename `serialize_into()`.
4. Introduce structured errors.
5. Add field selection, aliases, and exclusion.
6. Decide collection-subclass and middleware-subclass policies.

## Phase 3: Packaging and release discipline

1. Correct README imports and execute documentation examples in CI.
2. Commit a real license and align metadata.
3. Use tag-derived versions or enforce tag/version equality.
4. Test the installed package on all supported Python versions.
5. Add static typing, linting, build, wheel-install, and release checks.

# Proposed minimum release gate

Do not consider the deserializer stable until all of the following are true:

- [ ] constructors and dataclass `__post_init__` execute;
- [ ] slots and frozen dataclasses are tested;
- [ ] missing required fields fail;
- [ ] defaults and default factories are honored;
- [ ] unknown fields reject by default;
- [ ] non-optional targets reject `None`;
- [ ] all union branches, including optional unions, are handled correctly;
- [ ] validation and coercion are separate policies;
- [ ] unexpected exceptions are not swallowed by union matching;
- [ ] collection subclasses do not silently lose data;
- [ ] dictionary key behavior is explicit;
- [ ] sensitive/private fields have an exclusion mechanism;
- [ ] middleware signatures match types and documentation;
- [ ] README examples run in CI;
- [ ] tests import the installed `pserialize` package;
- [ ] package metadata and license are consistent;
- [ ] release tags and package versions cannot diverge.

# Overall assessment

The project has a useful small-library shape and a reasonably readable implementation. The cycle detection and expanding typing support show good direction. However, the current object-construction model makes the deserializer fundamentally permissive in ways that are difficult for callers to reason about safely.

The central design rule for the next iteration should be:

> Deserialization must not create an object that normal construction would reject, unless the caller explicitly opts into an unsafe construction mode.

Enforcing that rule would resolve several of the highest-risk findings simultaneously and provide a sound basis for evolving the public API.