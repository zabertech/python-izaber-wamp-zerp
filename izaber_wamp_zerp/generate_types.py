import ast
import base64
import json
import keyword
import lzma
import os
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    TypedDict,
    TypeVar,
    Union,
    cast,
)

from izaber import initialize
from tqdm import tqdm

from izaber_wamp_zerp import zerp

initialize()


MODEL_DIRECTORY = os.path.join(Path(__file__).parent, "models")


# Zerp to Python field types.
Z2P_TYPES = {
    "boolean": "bool",
    "integer": "int",
    "integer_big": "int",
    "reference": "Union[str, Literal[False]]",
    "char": "str",
    "float": "float",
    "date": "str",
    "datetime": "str",
    "time": "str",
    "binary": "str",
    "selection": "str",
    "many2one": "Tuple[int, Any]",
    "one2many": "List[int]",
    "many2many": "List[int]",
    "serialized": "str",
    "text": "str",
    "string": "str",
    "int": "int",
    "url": "str",
}


# Base ORM module.
BASE_MODULE = "openerp.osv.orm"


# Base ZERP functions.
BASE_FUNCTIONS = [
    "create",
    "read",
    "write",
    "unlink",
    "search",
    "search_fetch",
]


# Argument filters.
BASE_ARGS = [
    "cr",
    "uid",
    "user",
]


DOMAIN_OPERATORS = [
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "like",
    "ilike",
    "in",
    "not in",
    "child_of",
    "parent_left",
    "parent_right",
]

SET_OPERATIONS = ["&", "|", "!"]


BASE_MODEL_NAME = "BaseModel"


def module(body: List[ast.AST], type_ignores: List[ast.TypeIgnore]) -> ast.Module:
    """Create an ast.Module node.

    Args:
        body: A list of the module's statements.
        type_ignores: A list of the module's type ignore comments.
    """
    module_node = ast.Module(
        body=body,
        type_ignores=type_ignores,
    )
    return module_node


def list_annotation(member_type: str) -> ast.Subscript:
    """Create an ast.Subscript node which represents a list annotation node of the given member type.

    Args:
        member_type: The member type of the list.
    """
    list_ident = "List"

    name_node = name(value=list_ident, ctx=ast.Load())
    type_node = name(value=member_type, ctx=ast.Load())

    node = ast.Subscript(
        value=name_node,
        slice=type_node,
        ctx=ast.Load(),
    )
    return node


def import_alias(name: str, asname: Union[str, None] = None) -> ast.alias:
    """Create an ast.alias node representing an import alias.

    Example:
        import_alias('foo', 'bar') -> foo as bar

    Args:
        name: The name of the object to import.
        asname: The alias.
    """
    alias_node = ast.alias(
        name=name,
        asname=asname,
    )
    return alias_node


def import_statement(names: List[ast.alias]) -> ast.Import:
    """Create an ast.Import node.

    Example:
        import_statement([ast.alias(name='x'), ast.alias(name='y')]) -> import x, y

    Args:
        names: A list of import alias nodes.
    """
    import_node = ast.Import(
        names=names,
    )
    return import_node


def import_from_statement(module: str, names: List[ast.alias], level: int = 0) -> ast.ImportFrom:
    """Create an ast.ImportFrom node.

    Example:
        import_from_statement('foo', [ast.alias(name='x'), ast.alias(name='y')], 0) -> from foo import x, y

    Args:
        module: The name of the module to import the requested "names" from.
        names: The list of import alias nodes.
        level: The level of the import, where:
            - 0: Absolute - from lib import x
            - 1: One level - from .lib import x
            - 2: Two levels - from ..lib import x
    """
    import_from_node = ast.ImportFrom(
        module=module,
        names=names,
        level=level,
    )
    return import_from_node


def create_import(names: List[str], from_module: str, *, level: int = 0) -> Union[ast.ImportFrom, ast.Import]:
    """Build an ast.Import or ast.ImportFrom statement for the given names.

    Example:
        create_import(["foo"], "bar", level=1) -> from .foo import bar

    Args:
        names: The list of names to be imported.
        from_module: The module to import the names from. If empty or None, a standard import statement is created.
        level: The level of the import.

    Returns:
        Union[ast.ImportFrom, ast.Import]: An `ast.ImportFrom` node if `from_module` is specified,
                                           otherwise an `ast.Import` node.
    """
    aliases = list(map(import_alias, names))

    if from_module:
        return import_from_statement(from_module, aliases, level=level)
    return import_statement(aliases)


def argument(name: str, annotation: Union[ast.Name, ast.Subscript, ast.Expr, None]) -> ast.arg:
    """Create an ast.arg node.

    Example:
        argument('foo', ast.Name('int', ctx=ast.Load())) -> foo: int

    Args:
        name: The name of the argument.
        annotation: The annotation of the argument.
    """
    arg_node = ast.arg(
        arg=name,
        annotation=annotation,
    )
    return arg_node


def function_call(
    function_name: Union[str, ast.Name, ast.Attribute],
    arguments: List[Union[ast.Constant, ast.Dict, ast.Name, ast.Starred]],
    keywords: List[ast.keyword],
) -> ast.Call:
    """Create an ast.Call node.

    Args:
        function_name: The name of the function.
        arguments: A list of the arguments passed by position.
        keywords: A list of the keyword arguments.
    """
    if isinstance(function_name, str):
        function_name = name(value=function_name, ctx=ast.Load())

    node = ast.Call(
        func=function_name,
        args=arguments,
        keywords=keywords,
    )
    return node


def constant(value: Any) -> ast.Constant:
    """Create an ast.Constant node.

    Args:
        value: The python object that the constant node represents.
    """
    arg_node = ast.Constant(
        value=value,
    )
    return arg_node


def arguments(args: List[ast.arg], defaults: List[ast.Constant]) -> ast.arguments:
    """Create an ast.arguments node with positional arguments.

    Args:
        args: List of positional `ast.arg` nodes.
        defaults: List of default arguments values, where List[-1] is the default value for the last argument.
    """
    args_node = ast.arguments(
        posonlyargs=[],
        args=args,
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        defaults=defaults,
    )
    return args_node


def name(value: str, ctx: Optional[Union[ast.Load, ast.Store]] = None) -> ast.Name:
    """Create an ast.Name node.

    Example:
        name("sale_order_record", ast.Load) -> sale_order_record:

    Args:
        value: The name as a string.
        ctx: Either ast.Load or ast.Store.
    """
    if not ctx:
        ctx = ast.Load()

    node = ast.Name(
        id=value,
        ctx=ctx,
    )
    return node


def function_definition(
    function_name: str,
    args: ast.arguments,
    body: List[ast.Expr],
    return_annotation: Union[ast.Name, ast.Constant, ast.Subscript, None] = None,
    decorators: Optional[List[ast.Name]] = None,
) -> ast.FunctionDef:
    """Create a ast.FunctionDef node.

    Args:
        function_name: The name of the function.
        args: An arguments node representing the arguments to the function.
        body: The list of nodes inside the function.
        return_annotation: The return annotation of the function.
        decorators: A list of decorators of the function.
    """
    if decorators is None:
        decorators = []

    node = ast.FunctionDef(
        name=function_name,
        args=args,
        body=body,
        decorator_list=decorators,
        returns=return_annotation,
        type_params=[],
    )
    return node


def variable_assignment(var_name: str, value: Union[ast.Call, ast.Constant]) -> ast.Assign:
    """Create an ast.Assign node.

    Example:
        variable_assignment("__modelname__", constant("my.class")) -> __modelname__ = "my.class"

    Args:
        var_name: The name of the variable.
        value: The value of the variable.
    """
    name_node = name(var_name, ast.Store())
    node = ast.Assign(
        targets=[name_node],
        value=value,
    )
    return node


def ellipsis_expression() -> ast.Expr:
    """Create an ast.Expr node representing an ellipsis."""
    expr_node = ast.Expr(value=constant(...))
    return expr_node


def class_definition(
    class_name: str,
    base_classes: List[str],
    body: List[Union[ast.AnnAssign, ast.Expr, ast.Assign, ast.FunctionDef]],
) -> ast.ClassDef:
    """Create an ast.ClassDef node.

    Args:
        class_name: The name of the class.
        base_classes: The classes that this class inherits.
        body: The contents of the class.
    """
    bases = map(name, base_classes)

    node = ast.ClassDef(
        name=class_name,
        bases=bases,
        keywords=[],
        body=body,
        decorator_list=[],
    )
    return node


def variable_annotation(variable_name: str, type_: str) -> ast.AnnAssign:
    """Create an ast.AnnAssign node.

    Example:
        variable_annotation("order_lines", "[]") -> order_lines: []

    Args:
        variable_name: The name of the variable.
        type_: The type of the annotation.
    """
    var_node = name(value=variable_name, ctx=ast.Load())
    annotation_node = name(value=type_, ctx=ast.Load())

    node = ast.AnnAssign(
        target=var_node,
        annotation=annotation_node,
        simple=1,
    )
    return node


def docstring(string: str) -> ast.Expr:
    """Create a docstring node.

    Args:
        string: The contents of the docstring.
    """
    node = ast.Expr(
        value=constant(string),
        kind=None,
    )
    return node


def dictionary(
    keys: List[Union[ast.Constant, ast.Name]],
    values: List[Union[ast.Constant, ast.Name]],
) -> ast.Dict:
    """Create an ast.Dict node.

    Args:
        keys: A list of nodes representing the keys in the dictionary.
        values: A list of nodes representing the values in the dictionary.
    """
    node = ast.Dict(
        keys=keys,
        values=values,
    )
    return node


def literal_annotation(elements: List[ast.Constant]) -> ast.Subscript:
    """Construct an ast.Subscript node representing a literal annotation.

    Args:
        elements: The list of elements inside the Literal.
    """
    node = ast.Subscript(
        value=name(value="Literal", ctx=ast.Load()),
        slice=ast.Tuple(
            elts=elements,
            ctx=ast.Load(),
        ),
    )
    return node


def fields_literal(
    variable_name: str,
    arguments: List[Union[str, bytes, int, None, bool, float]],
) -> ast.Assign:
    """Create an ast.Assign node representing a typing.Literal assignment.

    Example:
        fields_literal("v", ["field1", "field2", "field3"]) -> v = Literal['field1', 'field2', 'field3']

    Args:
        variable_name: The name of the variable.
        arguments: A list of arguments to the Literal.
    """
    target_node = name(value=make_fields_type_alias(variable_name), ctx=ast.Store())
    element_nodes = [constant(a) for a in arguments]
    subscript_node = literal_annotation(element_nodes)
    node = ast.Assign(
        targets=[target_node],
        value=subscript_node,
        ctx=ast.Load(),
    )
    return node


class BaseArgumentNode(ABC):
    """Base class for function arguments that require composed AST argument annotation nodes."""

    @classmethod
    @abstractmethod
    def get(cls, model_name: str, method_name: str, argument_name: str) -> Any:
        """Construct the AST node."""
        ...


class BaseReturnNode(ABC):
    """Base class for functions that require composed AST return annotation nodes."""

    @classmethod
    @abstractmethod
    def get(cls, model_name: str, method_name: str) -> Any:
        """Construct the AST node."""
        ...


class ReadFieldsNode(BaseArgumentNode):
    """Constructs an argument annotation node representing the 'fields' argument on 'read()' for a given model.

    Ie:

    fields: List[fields_model_name_record]
    """

    @classmethod
    def get(cls, model_name: str, method_name: str, argument_name: str) -> ast.arg:
        alias_name = make_fields_type_alias(make_read_model_classname(model_name))
        fields_annotation = list_annotation(alias_name)
        node = argument(argument_name, annotation=fields_annotation)
        return node


class ReadReturnsRecordNode(BaseReturnNode):
    """A return annotation node representing the return type of 'read()' for a given model.

    Ie:

    -> model_name_record
    """

    @classmethod
    def get(cls, model_name: str, method_name: str) -> ast.Name:
        return name(make_read_model_classname(model_name), ctx=ast.Load())


class ReadReturnsRecordListNode(BaseReturnNode):
    """A return annotation node representing the overloaded return type of 'read()' for a given model.

    Ie:

    -> List[model_name_record]
    """

    @classmethod
    def get(cls, model_name: str, method_name: str) -> ast.Subscript:
        return list_annotation(make_read_model_classname(model_name))


class SearchArgsNode(BaseArgumentNode):
    """Constructs an argument annotation node representing the 'args' domain argument on 'search()' for a given model.

    Ie:

    args: List[Union[SET_OPERATIONS, Tuple[fields_model_name_record, DOMAIN_OPERATORS, str]]]
    """

    @classmethod
    def get(cls, model_name: str, method_name: str, argument_name: str) -> ast.arg:
        fields_literal_name = make_fields_type_alias(make_read_model_classname(model_name))
        domain_operators_literal = literal_annotation([constant(a) for a in DOMAIN_OPERATORS])
        set_operations_literal = literal_annotation([constant(a) for a in SET_OPERATIONS])
        domain_tuple = ast.Subscript(
            value=name(value="Tuple"),
            slice=ast.Tuple(
                elts=[
                    name(value=fields_literal_name),
                    domain_operators_literal,
                    name(value="Any"),
                ],
                ctx=ast.Load(),
            ),
        )
        union = ast.Subscript(
            value=name("Union"),
            slice=ast.Tuple(elts=[set_operations_literal, domain_tuple]),
            ctx=ast.Load(),
        )
        list_ = ast.Subscript(
            name(value="List"),
            slice=union,
            ctx=ast.Load(),
        )
        expression = ast.Expr(
            value=list_,
        )
        node = argument(argument_name, annotation=expression)
        return node


class WriteValsNode(BaseArgumentNode):
    """Constructs an argument annotation node representing the "vals" argument on "write()" for a given model.

    Ie:

    vals: Dict[fields_model_name_record, Any]
    """

    @classmethod
    def get(cls, model_name: str, method_name: str, argument_name: str) -> ast.arg:
        fields_literal_name = make_fields_type_alias(make_read_model_classname(model_name))

        dict_tuple = ast.Subscript(
            value=name(value="Dict"),
            slice=ast.Tuple(
                elts=[
                    name(value=fields_literal_name),
                    name(value="Any"),
                ],
                ctx=ast.Load(),
            ),
        )
        expression = ast.Expr(
            value=dict_tuple,
        )
        node = argument(argument_name, annotation=expression)
        return node


BASE_TYPE_HINTS: Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]] = {
    "read": [
        {
            "overload": True,
            "arguments": {
                "ids": "List[int]",
                "context": "Optional[Dict[str, Any]]",
                "load": "Optional[str]",
                "fields": ReadFieldsNode,
            },
            "returns": ReadReturnsRecordListNode,
        },
        {
            "overload": True,
            "arguments": {
                "ids": "int",
                "context": "Optional[Dict[str, Any]]",
                "load": "Optional[str]",
                "fields": ReadFieldsNode,
            },
            "returns": ReadReturnsRecordNode,
        },
    ],
    "search": {
        "arguments": {
            "args": SearchArgsNode,
            "offset": "Optional[Union[int, Literal[False]]]",
            "limit": "Optional[Union[int, Literal[False]]]",
            "order": "Optional[Union[str, Literal[False]]]",
            "context": "Optional[Dict[str, Any]]",
            "count": "Optional[int]",
        },
        "returns": "List[int]",
    },
    "write": {
        "arguments": {
            "ids": "Union[int, List[int]]",
            "vals": WriteValsNode,
            "context": "Optional[Dict[str, Any]]",
        },
        "returns": None,
    },
    "unlink": {
        "arguments": {
            "ids": "Union[int, List[int]]",
            "context": "Optional[Dict[str, Any]]",
        },
        "returns": None,
    },
    "search_fetch": {
        "arguments": {
            "args": SearchArgsNode,
            "fields": ReadFieldsNode,
            "offset": "Optional[Union[int, Literal[False]]]",
            "limit": "Optional[Union[int, Literal[False]]]",
            "order": "Optional[Union[str, Literal[False]]]",
            "context": "Optional[Dict[str, Any]]",
            "count": "Optional[int]",
        },
        "returns": ReadReturnsRecordListNode,
    },
}


def infer_default(arg: Dict[str, Any]) -> Any:
    """Infer the Python type of a string representation of a Python object.

    Args:
        arg: The model metadata node to evaluate.
    """
    if not arg["has_default"]:
        return None
    try:
        obj = ast.literal_eval(arg["default"])
        return obj
    except SyntaxError:
        return arg["default"]


def construct_ast_node_from_string(
    value: str,
) -> Union[ast.Constant, ast.Subscript, ast.Name, ast.expr]:
    """Attempt to construct an AST node from a string representation of a type.

    Args:
        value: The string representation of a type.
    """
    tree = ast.parse(value)
    expr = cast(ast.Expr, tree.body[0])
    return expr.value


def get_base_type_hint_node(value: str, argument_name: str) -> ast.arg:
    """Generate an AST type-hint node for a base method argument defined in BASE_TYPE_HINTS.

    Args:
        value: The type hint.
        argument_name: The arguments name.
    """
    tree = ast.parse(value)
    expr = cast(ast.Expr, tree.body[0])
    node = cast(ast.Subscript, expr.value)
    arg_node = argument(argument_name, node)
    return arg_node


def get_argument_annotation_node(
    model_name: str,
    method_name: str,
    arg_name: str,
    overload_position: Optional[int] = None,
) -> ast.arg:
    """Construct an argument annotation node for the given argument.

    Args:
        model_name: The name of the model.
        method_name: The name of the method.
        arg_name: The name of the argument.
        overload_position: The overload position index.
    """
    if overload_position is not None:
        try:
            val = BASE_TYPE_HINTS[method_name][overload_position]["arguments"][arg_name]
        except KeyError:
            val = None
    else:
        try:
            val = BASE_TYPE_HINTS[method_name]["arguments"][arg_name]
        except KeyError:
            val = None

    if model_name == BASE_MODEL_NAME:
        val = None

    if isinstance(val, type) and issubclass(val, BaseArgumentNode) and arg_name:
        node = val.get(model_name, method_name, arg_name)
    elif isinstance(val, str) and arg_name:
        node = get_base_type_hint_node(val, arg_name)
    elif arg_name:
        node = argument(arg_name, annotation=name("Any", ctx=ast.Load()))
    else:
        raise TypeError(f"invalid annotation specified for {model_name}.{method_name}")

    return node


def get_return_annotation_node(
    model_name: str,
    method_name: str,
    overload_position: Optional[int] = None,
) -> Union[ast.Subscript, ast.Constant, None]:
    """Construct a return annotation node for the given model.

    Args:
        model_name: The name of the model.
        method_name: The name of the method.
        overload_position: The overload position index.
    """
    if model_name == BASE_MODEL_NAME:
        return name("Any", ctx=ast.Load())

    if overload_position is not None:
        val = BASE_TYPE_HINTS[method_name][overload_position]["returns"]
    else:
        try:
            val = BASE_TYPE_HINTS[method_name]["returns"]
        except KeyError:
            return name("Any", ctx=ast.Load())

    if not val:
        return name("Any", ctx=ast.Load())

    if isinstance(val, type) and issubclass(val, BaseReturnNode):
        node = val.get(model_name, method_name)
    elif isinstance(val, str):
        node = construct_ast_node_from_string(val)
    else:
        raise TypeError(f"invalid annotation specified for {model_name}.{method_name}")

    return node


class Field(TypedDict):
    type: str
    string: str
    help: Optional[str]
    size: Optional[int]
    required: bool
    select: bool
    selectable: bool
    source: str
    ownership: List[str]
    has_default: bool
    domain: Optional[List[List[str]]]
    context: Optional[Dict[str, Any]]


class ModelMetadataToASTHandler:
    @classmethod
    def function_arguments(
        cls,
        method_metadata: dict,
        model_name: str,
        method_name: str,
        overload_position: Optional[int] = None,
    ) -> ast.arguments:
        """Build an ast.arguments node representing the arguments defined in a methods metdata.

        Args:
            method_metadata: The metadata for this method.
            model_name: The name of the model.
            method_name: The name of the method.
            overload_position: The overload position index.
        """

        def parse_default(arg) -> ast.Constant:
            default = infer_default(arg)
            return constant(default)

        default_nodes = []
        arg_nodes = []

        for arg in method_metadata["args"]:
            arg_name = arg["name"]
            if arg_name in BASE_ARGS:
                continue
            if arg["has_default"]:
                default_nodes.append(parse_default(arg))
            node = get_argument_annotation_node(model_name, method_name, arg_name, overload_position)
            arg_nodes.append(node)

        return arguments(arg_nodes, default_nodes)

    @classmethod
    def docstring(cls, method_metadata: dict) -> Union[ast.Expr, None]:
        """Build an ast.Expr node representing the docstring defined in a methods metdata.

        Args:
            method_metadata: The metadata for this method.
            model_name: The name of the model.
            method_name: The name of the method.
            overload_position: The overload position index.
        """
        if not (method_metadata["doc"] and isinstance(method_metadata["doc"], list)):
            return None
        # Select an arbitrary docstring from the inheritance chain.
        doc = method_metadata["doc"][0]["doc"]
        docstring_node = docstring(doc)
        return docstring_node

    @classmethod
    def function_definition(
        cls,
        model_name: str,
        method_metadata: dict,
        method_name: str,
        overload_position: Optional[int] = None,
    ) -> ast.FunctionDef:
        """Construct an ast.FunctionDef node for a method from its metadata.

        Args:
            model_name: The name of the model containing the method.
            method_metadata: Metadata describing the method.
            method_name: The name of the method being defined.
            overload_position: The index of the overload.
        """
        function_body = []
        args_node = cls.function_arguments(method_metadata, model_name, method_name, overload_position)
        docstring_node = cls.docstring(method_metadata)
        if docstring_node:
            function_body.append(docstring_node)
        function_body.append(ellipsis_expression())
        returns = get_return_annotation_node(model_name, method_name, overload_position)
        decorator = cls.overload(method_name, overload_position)
        return function_definition(method_name, args_node, function_body, returns, decorator)

    @classmethod
    def field_annotations(cls, field_metadata: Dict[str, Field]) -> List[ast.AnnAssign]:
        """Construct type annotation nodes for each of the fields defined on a model.

        Args:
            field_metadata: The field metadata for the given model.
        """
        annotation_nodes = []

        for name, data in field_metadata.items():
            # Skip field names that are python keywords.
            # Example: 'global' on ir_rule.
            if keyword.iskeyword(name):
                continue
            python_type = Z2P_TYPES[data["type"]]
            node = variable_annotation(name, python_type)
            annotation_nodes.append(node)

        return annotation_nodes

    @classmethod
    def overload(
        cls,
        method_name: str,
        overload_position: int,
    ) -> Union[ast.Name, None]:
        """Construct an ast.Name node representing an `@overload` decorator if the given method is overloaded.

        Args:
            model_name: The name of the model.
            method_metadata: The methods metadata.
            method_name: The name of the method.
            overload_position: The overload position index.
        """
        try:
            overloaded = BASE_TYPE_HINTS[method_name][overload_position]["overload"]
        except (KeyError, TypeError):
            return None
        return [name(value="overload", ctx=ast.Load())] if overloaded else None

    @classmethod
    def build_function(
        cls,
        model_name: str,
        method_metadata: dict,
        method_name: str,
    ) -> List[ast.FunctionDef]:
        """Build an AST node of a function from its metadata, handling overloaded method signatures.

        Args:
            model_name: The name of the model.
            method_metadata: The methods metadata.
            method_name: The name of the method.
        """
        definitions: List[ast.FunctionDef] = []

        if method_name not in BASE_TYPE_HINTS:
            funcdef_node = cls.function_definition(model_name, method_metadata, method_name)
            definitions.append(funcdef_node)
            return definitions

        annotations = BASE_TYPE_HINTS[method_name]
        # Handle overloaded method signatures.
        if isinstance(annotations, list):
            for position in range(len(annotations)):
                funcdef_node = cls.function_definition(
                    model_name, method_metadata, method_name, overload_position=position,
                )
                definitions.append(funcdef_node)
        else:
            definitions.append(cls.function_definition(model_name, method_metadata, method_name))

        return definitions


def make_model_classname(identifier: str) -> str:
    """Convert a dotted model identifier into a snake_case classname.

    This function takes an identifier with dot notation (e.g., 'sale.order')
    and converts it into a snake_case format suitable for class names (e.g., 'sale_order').

    Args:
        identifier (str): The identifier string in dot notation.
    """
    return identifier.replace(".", "_")


def make_read_model_classname(identifier: str) -> str:
    """Convert a dotted model identifier into a snake_case classname with a '_record' suffix.

    This function takes an identifier with dot notation (e.g., 'sale.order')
    and converts it into a snake_case format with a '_record' suffix (e.g., 'sale_order_record').

    Args:
        identifier (str): The identifier string in dot notation.
    """
    new = identifier.replace(".", "_")
    return f"{new}_record"


def make_fields_type_alias(record_name: str) -> str:
    """Construct the name of the type alias used to enumerate the fields available on each model.

    Ie:

    fields_my_model_record = Literal['field1', 'field2', ...]

    Args:
        record_name (str): The name of the record for which to construct the type alias.
    """
    return f"fields_{record_name}"


def get_all_model_metadata() -> List[Dict[str, Any]]:
    """Retrieve the metadata for each model in the database."""
    obj = zerp.get("ir.model")
    compressed_data = obj.get_all_models_metadata_cached_json_compressed_b64()
    decoded = base64.b64decode(compressed_data)
    decompressed = lzma.decompress(decoded)
    return json.loads(decompressed)


def write_model(tree: Union[ast.Module, ast.ClassDef], path: str) -> None:
    """Write the source code represented by an AST node to a file.

    Args:
        tree: The AST node representing the source code.
        path: The file path where the source code will be written.
    """
    source = ast.unparse(tree)
    with open(path, "wb") as f:
        f.write(source.encode())


class Model(ABC):
    """Abstract base class for models that generate abstract syntax trees."""

    def __init__(self, model_name: str, model_metadata: Dict[str, Any]) -> None:
        """Initialize the model."""
        self.model_name = model_name
        self.model_metadata = model_metadata
        self.class_name = make_model_classname(self.model_name)
        self.record_name = make_read_model_classname(self.model_name)
        self.name = None

    @abstractmethod
    def generate_ast(self) -> Union[ast.Module, None]:
        """Generate an Abstract Syntax Tree (AST) for the model."""
        ...

    @abstractmethod
    def write(self, tree: ast.Module) -> None:
        """Write the AST to a file."""
        ...

    def create(self) -> None:
        """Generate and write the model's AST to a file."""
        tree = self.generate_ast()
        if tree:
            self.write(tree)


class TableModel(Model):
    """Represents the method signatures available on a particular model."""

    def generate_ast(self) -> Union[ast.Module, None]:
        """Generate an AST module tree representing the method signatures of the model.

        Returns:
            ast.Module: An AST module node representing the model's method signatures or None if no methods are defined.
        """
        if not self.model_metadata["methods"]:
            return None

        body_nodes: List[Union[ast.AnnAssign, ast.Expr, ast.Assign, ast.FunctionDef]] = []

        field_name = make_fields_type_alias(self.record_name)
        import_node = create_import([self.record_name, field_name], self.record_name, level=1)
        base_import_node = create_import([BASE_MODEL_NAME], "base", level=1)
        typing_import_node = create_import(
            [
                "Any",
                "Dict",
                "List",
                "Literal",
                "Optional",
                "Tuple",
                "Union",
                "overload",
            ],
            "typing",
            level=0,
        )

        methods = self.model_metadata["methods"]
        for method, method_metadata in methods.items():
            if method_metadata["module"] == BASE_MODULE and method not in BASE_FUNCTIONS:
                continue
            function_nodes = ModelMetadataToASTHandler.build_function(
                self.model_name, method_metadata, method,
            )
            body_nodes.extend(function_nodes)

        class_node = class_definition(self.class_name, [BASE_MODEL_NAME], body_nodes)
        module_node = module([typing_import_node, import_node, base_import_node, class_node], [])
        new_tree = ast.fix_missing_locations(module_node)
        return new_tree

    def write(self, tree: ast.Module) -> None:
        path = os.path.join(MODEL_DIRECTORY, self.class_name + ".py")
        return write_model(tree, path)


class RecordModel(Model):
    """A TypedDict representing the columns, and their types, available on each model."""

    def generate_ast(self) -> Union[ast.Module, None]:
        """Generate the AST describing a models columns.

        Generate an AST module node of a TypedDict class containing the names and type
        information of each column available on the model.

        Returns:
            ast.Module: An AST module node representing the TypedDict class for the model.
        """
        annotation_nodes: List[Union[ast.AnnAssign, ast.Expr, ast.Assign, ast.FunctionDef]] = []

        fields = self.model_metadata["fields"]
        typing_import_node = create_import(
            [
                "Any",
                "Dict",
                "List",
                "Literal",
                "Optional",
                "Tuple",
                "Union",
                "TypedDict",
            ],
            "typing",
            level=0,
        )
        keys = fields.keys() if fields else [None]
        fields_definition = fields_literal(self.record_name, keys)
        if fields:
            annotation_nodes.extend(ModelMetadataToASTHandler.field_annotations(fields))
        else:
            annotation_nodes.append(ellipsis_expression())
        class_node = class_definition(self.record_name, ["TypedDict"], annotation_nodes)
        module_node = module([typing_import_node, fields_definition, class_node], [])
        new_tree = ast.fix_missing_locations(module_node)
        return new_tree

    def write(self, tree: ast.Module) -> None:
        path = os.path.join(MODEL_DIRECTORY, self.record_name + ".py")
        return write_model(tree, path)


class BaseModel(Model):
    """Represents the base ORM methods available to each model."""

    def generate_ast(self) -> Union[ast.Module, None]:
        """Generate an AST describing the base methods available on the ORM.

        Returns:
            ast.Module: An AST module node representing the BaseModel.
        """
        function_nodes: List[Union[ast.AnnAssign, ast.Expr, ast.Assign, ast.FunctionDef]] = []

        typing_import_node = create_import(["Any"], "typing", level=0)
        methods = self.model_metadata["methods"]
        for method, method_metadata in methods.items():
            if method_metadata["module"] != BASE_MODULE:
                continue
            function_node = ModelMetadataToASTHandler.function_definition(
                self.model_name, method_metadata, method
            )
            function_nodes.append(function_node)

        class_node = class_definition(self.model_name, [], function_nodes)
        module_node = module([typing_import_node, class_node], [])
        new_tree = ast.fix_missing_locations(module_node)
        return new_tree

    def write(self, tree: ast.Module) -> None:
        path = os.path.join(MODEL_DIRECTORY, "base.py")
        return write_model(tree, path)


class TypedZERPModel(Model):
    """Represents a TypedDict for providing type hints to the `zerp` singleton."""

    def generate_ast(self) -> Union[ast.Module, None]:
        """Generate the AST for the TypedZERP class providing type hints to the `zerp` singleton.

        Returns:
            ast.Module: An AST module node representing the TypedZERP class.
        """
        table_to_model_names = {
            t: make_model_classname(t) for t in self.model_metadata if self.model_metadata[t]
        }
        # Setup the imports.
        import_nodes = []
        import_nodes.append(create_import(["TypedDict"], "typing", level=0))
        for model_name in table_to_model_names.values():
            import_nodes.append(create_import([model_name], model_name, level=1))

        var_node = constant("TypedZERP")
        dict_node = dictionary(
            keys=list(map(constant, table_to_model_names.keys())),
            values=list(map(name, table_to_model_names.values())),
        )
        function_call_node = function_call("TypedDict", [var_node, dict_node], [])
        variable_node = variable_assignment("TypedZERP", value=function_call_node)
        module_node = module(body=[*import_nodes, variable_node], type_ignores=[])
        tree = ast.fix_missing_locations(module_node)
        return tree

    def write(self, tree):
        model_type_hint_path = os.path.join(MODEL_DIRECTORY, "zerp.py")
        return write_model(tree, model_type_hint_path)


@dataclass
class ModelProgress:
    success: int = 0
    ignored: int = 0
    errors: int = 0
    total: int = 0


TDisplayHandler = TypeVar("TDisplayHandler", bound="DisplayHandler")


class DisplayHandler:
    """Handler for displaying the progress of the model generation process."""

    def __init__(self, total: int):
        self.progress = ModelProgress(total=total)
        self.successes: List[str] = []
        self.progress_bar = tqdm(
            total=total,
            desc="Generating models",
            bar_format="{l_bar}{bar:10}| {n_fmt}/{total_fmt}",
        )

    def ignore(self, model_name: str) -> None:
        """Mark a model as ignored.

        Args:
            model_name: The name of the model.
        """
        self.progress.ignored += 1
        self.success(model_name)

    def error(self, model_name: str) -> None:
        """Mark a model as failed to generate.

        Args:
            model_name: The name of the model.
        """
        self.progress.errors += 1

    def success(self, model_name: str) -> None:
        """Update and output the current progress.

        Args:
            model_name: The name of the model currently being loaded.
        """
        self.progress.success += 1
        self.progress_bar.update(1)
        self.successes.append(model_name)

    def __enter__(self: TDisplayHandler) -> TDisplayHandler:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Output a summary upon completion."""
        self.progress_bar.close()
        summary = textwrap.dedent(f"""
        {self.progress.success}/{self.progress.total} models successfully generated.
        - {self.progress.ignored}/{self.progress.total} stale models ignored.
        - {self.progress.errors}/{self.progress.total} models failed to generate.
        """)
        print(summary)


def run(ignore_errors: bool = False) -> None:
    """Run the model generation.

    Args:
        fail_on_error: Fail gracelessly when a model generation error is encountered
    """
    model_metadata = get_all_model_metadata()

    # Create the base model.
    BaseModel(BASE_MODEL_NAME, model_metadata["ir.model"]).create()

    type_models: List[Type[Model]] = [RecordModel, TableModel]

    with DisplayHandler(len(model_metadata)) as handler:
        for model_name, metadata in model_metadata.items():
            if not metadata:
                handler.ignore(model_name)
                continue
            try:
                for type_model in type_models:
                    type_model(model_name, metadata).create()
            except:  # noqa: E722
                if not ignore_errors:
                    raise
                handler.error(model_name)
            else:
                handler.success(model_name)

        # Create the TypedZERP model using only the models that were successfully generated.
        filtered_model_metadata = {model: model_metadata[model] for model in handler.successes}
        TypedZERPModel("TypedZERPModel", filtered_model_metadata).create()


if __name__ == "__main__":
    run()
