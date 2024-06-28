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
    """Creates a ast.Subscript node which represents a list annotation node of the given member type.

    Args:
        member_type: The member type of the list.
    """
    LIST_IDENT = "List"

    name_node = name(value=LIST_IDENT, ctx=ast.Load())
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


def name(value: str, ctx: Union[ast.Load, ast.Store] = ast.Load()) -> ast.Name:
    """Create an ast.Name node.

    Example:
        name("sale_order_record", ast.Load) -> sale_order_record:

    Args:
        value: The name as a string.
        ctx: Either ast.Load or ast.Store.
    """
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
        base_class: The class that this class inherits.
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


def variable_annotation(variable_name: str, type: str) -> ast.AnnAssign:
    """Create an ast.AnnAssign node.

    Example:
        variable_annotation("order_lines", "[]") -> order_lines: []

    Args:
        variable_name: The name of the variable.
        type: The type of the annotation.
    """
    var_node = name(value=variable_name, ctx=ast.Load())
    annotation_node = name(value=type, ctx=ast.Load())

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


def literal(
    variable_name: str,
    arguments: List[Union[str, bytes, int, None, Literal[False], Literal[True], bool]],
) -> ast.Assign:
    """Create an ast.Assign node which represents a typing.Literal assignment.

    Example:
        literal("v", ["field1", "field2", "field3"]) -> v = Literal['field1', 'field2', 'field3']

    Args:
        variable_name: The name of the variable.
        arguments: A list of arguments to the Literal.
    """
    target_node = name(value=make_fields_type_alias(variable_name), ctx=ast.Store())
    elt_nodes = [ast.Constant(value=a) for a in arguments]
    subscript_node = ast.Subscript(
        value=name(value="Literal", ctx=ast.Load()),
        slice=ast.Tuple(
            elts=elt_nodes,
            ctx=ast.Load(),
        ),
    )
    node = ast.Assign(
        targets=[target_node],
        value=subscript_node,
        ctx=ast.Load(),
    )
    return node


def get_fields_type_hint(model_name: str, method_name: str, argument_name: str) -> ast.arg:
    """Generate the type hint for the 'fields' argument on 'read' for a given model.

    This is generally a list of the canonical fields_*_record class for a particular model.

    Ie:

    fields: List[fields_zerp_yearly_sales_per_partner_record]

    Args:
        method_name: The name of the method.
        argument_name: The name of the argument.
    """
    alias_name = make_fields_type_alias(make_read_model_classname(model_name))
    fields_annotation = list_annotation(alias_name)
    node = argument(argument_name, annotation=fields_annotation)
    return node


def get_args_type_hint(model_name: str, method_name: str, argument_name: str) -> ast.arg:
    """Generate the type hint for the "args" domain argument on "search" for a given model.

    This takes the form:
        List[Union[SET_OPERATIONS, Tuple[fields_record_name, DOMAIN_OPERATORS, str]]]

    Args:
        model_name: The name of the model.
        method_name: The name of the method.
        argument_name: The name of the argument.
    """
    fields_literal_name = make_fields_type_alias(make_read_model_classname(model_name))
    # TODO: cleanup
    elt_nodes = [ast.Constant(value=a) for a in DOMAIN_OPERATORS]
    domain_operators_literal = ast.Subscript(
        value=name(value="Literal", ctx=ast.Load()),
        slice=ast.Tuple(
            elts=elt_nodes,
            ctx=ast.Load(),
        ),
    )

    elt_nodes = [ast.Constant(value=a) for a in SET_OPERATIONS]
    set_operations_literal = ast.Subscript(
        value=name(value="Literal", ctx=ast.Load()),
        slice=ast.Tuple(
            elts=elt_nodes,
            ctx=ast.Load(),
        ),
    )

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
    list = ast.Subscript(
        name(value="List"),
        slice=union,
        ctx=ast.Load(),
    )
    expression = ast.Expr(
        value=list,
    )
    node = argument(argument_name, annotation=expression)
    return node


def get_vals_type_hint(model_name: str, method_name: str, argument_name: str) -> ast.arg:
    """Generate the type hint for the "vals" argument on "write".

    This takes the form:
        Dict[Literal[field, ...,], Any]

    Args:
        model_name: The name of the model.
        method_name: The name of the method.
        argument_name: The name of the argument.
    """
    fields_literal_name = make_fields_type_alias(make_read_model_classname(model_name))

    # TODO: Cleanup
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


def get_read_return_annotation(model_name: str) -> ast.Subscript:
    return list_annotation(make_read_model_classname(model_name))


class BaseArgumentNode(ABC):
    @classmethod
    @abstractmethod
    def get(cls, model_name: str, method_name: str, argument_name: str):
        ...


class BaseReturnNode(ABC):
    @classmethod
    @abstractmethod
    def get(cls, model_name: str, method_name: str):
        ...


class ReadFieldsNode(BaseArgumentNode):
    @classmethod
    def get(cls, model_name: str, method_name: str, argument_name: str) -> ast.arg:
        alias_name = make_fields_type_alias(make_read_model_classname(model_name))
        fields_annotation = list_annotation(alias_name)
        node = argument(argument_name, annotation=fields_annotation)
        return node


class ReadReturnsRecordListNode(BaseReturnNode):
    @classmethod
    def get(cls, model_name: str, method_name: str) -> ast.Subscript:
        return list_annotation(make_read_model_classname(model_name))


class ReadReturnsRecordNode(BaseReturnNode):
    @classmethod
    def get(cls, model_name: str, method_name: str) -> ast.Name:
        return name(make_read_model_classname(model_name), ctx=ast.Load())


class SearchArgsNode(BaseArgumentNode):
    @classmethod
    def get(cls, model_name: str, method_name: str, argument_name: str) -> ast.arg:
        """Generate the type hint for the "args" domain argument on "search" for a given model.

        This takes the form:
            List[Union[SET_OPERATIONS, Tuple[fields_record_name, DOMAIN_OPERATORS, str]]]

        Args:
            model_name: The name of the model.
            method_name: The name of the method.
            argument_name: The name of the argument.
        """
        fields_literal_name = make_fields_type_alias(make_read_model_classname(model_name))
        # TODO: cleanup
        elt_nodes = [ast.Constant(value=a) for a in DOMAIN_OPERATORS]
        domain_operators_literal = ast.Subscript(
            value=name(value="Literal", ctx=ast.Load()),
            slice=ast.Tuple(
                elts=elt_nodes,
                ctx=ast.Load(),
            ),
        )

        elt_nodes = [ast.Constant(value=a) for a in SET_OPERATIONS]
        set_operations_literal = ast.Subscript(
            value=name(value="Literal", ctx=ast.Load()),
            slice=ast.Tuple(
                elts=elt_nodes,
                ctx=ast.Load(),
            ),
        )

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
        list = ast.Subscript(
            name(value="List"),
            slice=union,
            ctx=ast.Load(),
        )
        expression = ast.Expr(
            value=list,
        )
        node = argument(argument_name, annotation=expression)
        return node


class WriteValsNode(BaseArgumentNode):
    @classmethod
    def get(cls, model_name: str, method_name: str, argument_name: str) -> ast.arg:
        """Generate the type hint for the "vals" argument on "write".

        This takes the form:
            Dict[Literal[field, ...,], Any]

        Args:
            model_name: The name of the model.
            method_name: The name of the method.
            argument_name: The name of the argument.
        """
        fields_literal_name = make_fields_type_alias(make_read_model_classname(model_name))

        # TODO: Cleanup
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
}


def infer_default(arg: dict) -> Any:
    """Infer the Python type of a string representation of a Python object.

    Args:
        arg: The model metadata node to evaluate.
    """
    if not arg["has_default"]:
        return
    try:
        obj = ast.literal_eval(arg["default"])
        return obj
    except SyntaxError:
        return arg["default"]


def construct_ast_node_from_string(
    value: str,
) -> Union[ast.Constant, ast.Subscript, ast.Name, ast.expr]:
    """Attempt to construct an AST node from a string representation of a type.

    # TODO: Cleanup

    Args:
        value: The string representation of a type.
    """
    tree = ast.parse(value)
    expr = cast(ast.Expr, tree.body[0])
    if isinstance(expr.value, ast.Subscript):
        return cast(ast.Subscript, expr.value)
    elif isinstance(expr.value, ast.Name):
        return cast(ast.Name, expr.value)
    elif isinstance(expr.value, ast.Constant):
        return cast(ast.Constant, expr.value)
    return expr.value


def get_base_type_hint_node(value: str, argument_name: str) -> ast.arg:
    """Generate an AST type-hint node for a base method argument defined in BASE_TYPE_HINTS.

    Args:
        method_name: The base methods name.
        argument_name: The arguments name.
    """
    # node = construct_ast_node_from_string(value)
    # arg_node = argument(argument_name, node)
    # return arg_node
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

    if model_name == "BaseModel":
        val = None

    if isinstance(val, type) and issubclass(val, BaseArgumentNode) and arg_name:
        node = val.get(model_name, method_name, arg_name)
    elif isinstance(val, str) and arg_name:
        node = get_base_type_hint_node(val, arg_name)
    elif arg_name:
        node = argument(arg_name, annotation=None)
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
    """
    if model_name == "BaseModel":
        return None

    if overload_position is not None:
        val = BASE_TYPE_HINTS[method_name][overload_position]["returns"]
    else:
        try:
            val = BASE_TYPE_HINTS[method_name]["returns"]
        except KeyError:
            return None

    if not val:
        return None

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
    ownership: List
    has_default: bool
    domain: Optional[List]
    context: Optional[dict]


class ModelMetadataToASTHandler:
    @classmethod
    def function_arguments(
        cls,
        method_metadata: dict,
        model_name: str,
        method_name: str,
        overload_position: Optional[int] = None,
    ) -> ast.arguments:
        """Translate a method defined in model metadata to an ast.arguments node.

        Args:
            method_metadata:
            method_name:
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
        """Generate an AST function definition node for a method based on its metadata.

        This method creates an AST function definition node, including arguments, docstring,
        and a placeholder body.

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
        decorator = cls.overload(model_name, method_metadata, method_name, overload_position)
        return function_definition(method_name, args_node, function_body, returns, decorator)

    @classmethod
    def field_annotations(cls, field_metadata: Dict[str, Field]) -> List[ast.AnnAssign]:
        """Construct type annotations for each of the fields available on a model.

        Args:
            field_metadata: The field metadata for the given model.
        """
        annotation_nodes = []

        for name, data in field_metadata.items():
            # TODO: Instead, change the name of the field to "name_"
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
        model_name: str,
        method_metadata: dict,
        method_name: str,
        overload_position: int,
    ) -> Union[ast.Name, None]:
        """Return an ast.Name node representing an `@overload` decorator if the given method is overloaded."""
        try:
            overloaded = BASE_TYPE_HINTS[method_name][overload_position]["overload"]
        except (KeyError, TypeError):
            return None
        return [name(value="overload", ctx=ast.Load())] if overloaded else None

    @classmethod
    def build_function(
        cls, model_name: str, method_metadata: dict, method_name: str
    ) -> List[ast.FunctionDef]:
        definitions: List[ast.FunctionDef] = []
        if method_name not in BASE_TYPE_HINTS:
            definitions.append(cls.function_definition(model_name, method_metadata, method_name))
            return definitions
        annotations = BASE_TYPE_HINTS[method_name]
        if isinstance(annotations, list):
            for position in range(len(annotations)):
                definition = cls.function_definition(
                    model_name, method_metadata, method_name, overload_position=position
                )
                definitions.append(definition)
            return definitions
        else:
            definitions.append(cls.function_definition(model_name, method_metadata, method_name))
            return definitions


def make_model_classname(identifier: str) -> str:
    """Convert a dotted identifier into a snake_case classname.

    This function takes an identifier with dot notation (e.g., 'sale.order')
    and converts it into a snake_case format suitable for class names (e.g., 'sale_order').

    Args:
        identifier (str): The identifier string in dot notation.
    """
    return identifier.replace(".", "_")


def make_read_model_classname(identifier: str) -> str:
    """Convert a dotted identifier into a snake_case classname with a '_record' suffix.

    This function takes an identifier with dot notation (e.g., 'sale.order')
    and converts it into a snake_case format with a '_record' suffix (e.g., 'sale_order_record').

    Args:
        identifier (str): The identifier string in dot notation.
    """
    new = identifier.replace(".", "_")
    return f"{new}_record"


def make_fields_type_alias(record_name: str) -> str:
    """Construct the name of the type alias used to define the fields available on each model.

    Example: fields_my_model_record = Literal['field1', 'field2', ...]

    Args:
        record_name (str): The name of the record for which to construct the type alias.
    """
    return f"fields_{record_name}"


def get_all_model_metadata():
    """Retrieve the metadata for each model in the database from the server."""
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

    def __init__(self, model_name: str, model_metadata):
        self.model_name = model_name
        self.model_metadata = model_metadata
        self.class_name = make_model_classname(self.model_name)
        self.record_name = make_read_model_classname(self.model_name)

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
        # TODO: constant for this
        base_import_node = create_import(["BaseModel"], "base", level=1)
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
                self.model_name, method_metadata, method
            )
            body_nodes.extend(function_nodes)
            # function_node = ModelMetadataToASTHandler.function_definition(self.model_name, method_metadata, method)
            # body_nodes.append(function_node)

        class_node = class_definition(self.class_name, ["BaseModel"], body_nodes)
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
        fields_definition = literal(self.record_name, keys)
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

        methods = self.model_metadata["methods"]
        for method, method_metadata in methods.items():
            if method_metadata["module"] != BASE_MODULE:
                continue
            function_node = ModelMetadataToASTHandler.function_definition(
                self.model_name, method_metadata, method
            )
            function_nodes.append(function_node)

        class_node = class_definition(self.model_name, [], function_nodes)
        module_node = module([class_node], [])
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

        import_nodes = []

        # Setup the imports.
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


def run(fail_on_error: bool = False) -> None:
    """Run the model generation.

    Args:
        fail_on_error: Fail gracelessly when a model generation error is encountered
    """
    model_metadata = get_all_model_metadata()

    # Create the base model.
    BaseModel("BaseModel", model_metadata["ir.model"]).create()

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
                if fail_on_error:
                    raise
                handler.error(model_name)
            else:
                handler.success(model_name)

        # Create the TypedZERP model using the models that were successfully generated.
        filtered_model_metadata = {model: model_metadata[model] for model in handler.successes}
        TypedZERPModel("TypedZERPModel", filtered_model_metadata).create()


if __name__ == "__main__":
    run()
