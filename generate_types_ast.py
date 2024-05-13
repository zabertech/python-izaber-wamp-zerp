import ast
import json
import keyword
import os

from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union

from izaber import initialize
from izaber_wamp_zerp import zerp


initialize()


# Model directory.
MODEL_DIRECTORY = os.path.join(Path(__file__).parent, "izaber_wamp_zerp", "models_ast")

if not os.path.exists(MODEL_DIRECTORY):
    os.mkdir(MODEL_DIRECTORY)

# Zerp to Python field type mappings.
# 'function' and 'related' fields are replaced with their underlying types in `model_metadata`.
Z2P_TYPES = {
    'boolean': 'bool',
    'integer': 'int',
    'integer_big': 'int',
    'reference': 'Union[str, Literal[False]]', # Example: 'purchase.order.line,59502'
    'char': 'str',
    'float': 'float',
    'date': 'str',
    'datetime': 'str',
    'time': 'str',
    'binary': 'str', # bytes?
    'selection': 'str',
    'many2one': 'Tuple[int, Any]',  # Example: [1, 'Zaber Technologies Inc'] via name_get?
    'one2many': 'List[int]',
    'many2many': 'List[int]',
    'serialized': 'str',
    'text': 'str',
    'string': 'str',
    'int': 'int',
}


# Base ORM module.
BASE_MODULE = 'openerp.osv.orm'


# Base ZERP functions.
BASE_FUNCTIONS = [
    'create',
    'read',
    'write',
    'unlink',
]


# Argument filters.
BASE_ARGS = [
    'cr',
    'uid',
    'user',
]


BASE_TYPE_HINTS = {
    # def read(self, ids, fields='_classic_read', context=None, load=None)
    'read': {
        'ids': 'Union[List[int], Literal[False]]',  # Compatible with an empty list.
        'context': 'Optional[Dict[str, Any]]',
        'load': 'Optional[str]',
    },
    # def search(self, args, offset=False, limit=None, order=None, context=None, count=0)
    'search': {
        'args': 'List[Tuple[str, ...]]',
        'offset': 'Optional[Union[int, Literal[False]]]',
        'limit': 'Optional[Union[int, Literal[False]]]',
        'order': 'Optional[Union[str, Literal[False]]]',
        'context': 'Optional[Dict[str, Any]]',
        'count': 'Optional[int]',
    },
    # def write(self, ids, vals, context=None)
    'write': {
        'ids': 'List[int]',
        'vals': 'Dict[str, Any]', # TODO: Type should be Dict[fields_model, Any]
        'context': 'Optional[Dict[str, Any]]',
    },
    # def unlink(self, ids, context=None)
    'unlink': {
        'ids': 'List[int]',
        'context': 'Optional[Dict[str, Any]]',
    }
}


def module(body: List[Any], type_ignores: List) -> ast.Module:
    module_node = ast.Module(
        body=body,
        type_ignores=type_ignores,
    )
    return module_node


def list_annotation(member_type: str) -> ast.Subscript:
    """Creates a list annotation node that can be used to type hint a function argument.

    Example:

    ```
    ids: List[int]

    Becomes:

    annotation=Subscript(
        value=Name(id='List', ctx=Load()),
        slice=Name(id='int', ctx=Load()),
        ctx=Load())),
    ```
    """
    LIST_IDENT = "List"

    name_node = ast.Name(id=LIST_IDENT, ctx=ast.Load())
    type_node = ast.Name(id=member_type, ctx=ast.Load())

    node = ast.Subscript(
        value=name_node,
        slice=type_node,
        ctx=ast.Load(),
    )
    return node


def import_alias(name: str, asname: Union[str, None]) -> ast.alias:
    """Create an import alias node.

    Example:

    import_alias('foo', 'bar')

    Creates:

    foo as bar

    Which can be used in an import or import_from node.
    """
    alias_node = ast.alias(
        name=name,
        asname=asname,
    )
    return alias_node


def import_aliases(*args: str) -> List[ast.alias]:
    """Create a list of imports.
    
    Example:

    import_aliases('x', 'y', 'z')

    Creates:

    x, y, z

    Which can be used in an import or import_from node.
    """
    aliases = [import_alias(arg, None) for arg in args]
    return aliases


def import_statement(names: List[ast.alias]) -> ast.Import:
    """Create an 'import' node.

    Example:

    import_statement([ast.alias(name='x'), ast.alias(name='y')])

    Creates:

    import x, y
    """
    import_node = ast.Import(
        names=names,
    )
    return import_node


def import_from_statement(module: str, names: List[ast.alias], level: int=0) -> ast.ImportFrom:
    """Create an 'import from' node.

    level: Level of the relative import, where:
        0: Absolute - from lib import x
        1: One level - from .lib import x
        2: Two levels - from ..lib import x

    Example:

    import_from_statement('foo', [ast.alias(name='x'), ast.alias(name='y')], 0)

    Creates:

    from foo import x, y
    """
    import_from_node = ast.ImportFrom(
        module=module,
        names=names,
        level=level,
    )
    return import_from_node


def argument(name, annotation: Union[ast.Name, ast.Subscript]) -> ast.arg:
    """Create an 'arg' node.
    
    Example:

    argument('foo', ast.Name('int', ctx=ast.Load()))

    Creates:

    foo: int

    For:

    def bar(foo: int): ...
    """
    arg_node = ast.arg(
        arg=name,
        annotation=annotation,
    )
    return arg_node


def constant(value) -> ast.Constant:
    """Create a 'constant' node.
    
    The value attribute of the Constant literal contains the Python object it represents. 
    The values represented can be simple types such as a number, string or None, but also immutable 
    container types (tuples and frozensets) if all of their elements are constant.
    """
    arg_node = ast.Constant(
        value=value,
    )
    return arg_node


def function_arguments(args: List[ast.arg], defaults: List[ast.Constant]) -> ast.arguments:
    """
    Args: List of `ast.arg` nodes. These are arguments that can be both positional or keyword.
    Defaults: List of default arguments values, where List[-1] is the default value for the last argument.
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


def function_return_annotation(value: str) -> ast.Name:
    """
    Example:

    function_return_annotation("sale_order_record")

    Creates:

    -> sale_order_record:
    """
    node = ast.Name(
        id=value,
        ctx=ast.Load(),
    )
    return node


def function_definition(function_name: str, args: ast.arguments, body: List, return_annotation: ast.Name):
    node = ast.FunctionDef(
        name=function_name,
        args=args,
        body=body,
        decorator_list=[],
        returns=return_annotation,
        type_params=[],
    )
    return node


def variable_assignment(var_name: str, value: ast.Constant) -> ast.Assign:

    """
    __modelname__ = "my.class"

    Becomes:

    Assign(
        targets=[
            Name(id='__modelname__', ctx=Store())],
        value=Constant(value='my.class')),
    """
    name_node = ast.Name(
        id=var_name,
        ctx=ast.Store(),
    )
    node = ast.Assign(
        targets=[name_node],
        value=value,
    )
    return node


def ellipsis_expression():
    expr_node = ast.Expr(
        value=constant(...)
    )
    return expr_node


def class_definition(class_name: str, base_class: str, body: List) -> ast.ClassDef:
    bases = []
    if base_class:
        base_class = ast.Name(id=base_class, ctx=ast.Load())
        bases.append(base_class)

    node = ast.ClassDef(
        name=class_name,
        bases=bases,
        keywords=[],
        body=body,
        decorator_list=[],
    )
    return node


def variable_annotation(variable_name: str, type: str) -> ast.Expression:
    """
    Example:

    variable_annotation("order_lines", "[]")

    order_lines: []
    """
    var_node = ast.Name(id=variable_name, ctx=ast.Load())
    annotation_node = ast.Name(id=type, ctx=ast.Load())

    node = ast.AnnAssign(
        target=var_node,
        annotation=annotation_node,
        simple=1,
    )
    return node


def docstring(string: str) -> ast.Expr:
    """
    FunctionDef(
        name='read',
        args=arguments(
            posonlyargs=[],
            args=[
                arg(arg='self'),
                arg(arg='cr'),
                arg(arg='uid'),
                arg(
                    arg='ids',
                    annotation=Subscript(
                        value=Name(id='List', ctx=Load()),
                        slice=Name(id='int', ctx=Load()),
                        ctx=Load())),
                arg(arg='context'),
                arg(arg='strfield')],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[
                Constant(value=None),
                Constant(value='mystring')]),
        body=[
            Expr(
                value=Constant(value='Arbitrary docstring.'))],
        decorator_list=[],
        returns=Subscript(
            value=Name(id='List', ctx=Load()),
            slice=Name(id='ReadRecord', ctx=Load()),
            ctx=Load()))
    """    
    node = ast.Expr(
        value=constant(string),
        kind=None,
    )
    return node


def infer_default(arg: dict):
    if not arg["has_default"]:
        return
    try:
        obj = ast.literal_eval(arg["default"])
        return obj
    except SyntaxError:
        return arg["default"]
    

def fields_variable_identifier(record_name: str) -> str:
    return f"fields_{record_name}"


def fields_type_definition(recordname: str, fields: list) -> ast.Assign:
    """
    fields_recordname = Literal['field1', 'field2', 'field3'...]

    Creates:

    Assign(
        targets=[
            Name(id='items', ctx=Store())],
        value=Subscript(
            value=Name(id='Literal', ctx=Load()),
            slice=Tuple(
                elts=[
                    Constant(value='hello'),
                    Constant(value='hi'),
                    Constant(value='yes'),
                    Constant(value='ok')],
                ctx=Load()),
            ctx=Load())),
    """
    target_node = ast.Name(
        id=fields_variable_identifier(recordname),
        ctx=ast.Store(),
    )
    elt_nodes = [ast.Constant(value=field) for field in fields]
    subscript_node = ast.Subscript(
        value=ast.Name(
            id='Literal',
            ctx=ast.Load(),
        ),
        slice=ast.Tuple(
            elts=elt_nodes,
            ctx=ast.Load(),
        )
    )
    node = ast.Assign(
        targets=[target_node],
        value=subscript_node,
        ctx=ast.Load(),
    )
    return node


def get_base_type_hint_node(method_name: str, argument_name: str) -> ast.arg:
    """Generate an AST type-hint node from a string."""
    hint = BASE_TYPE_HINTS[method_name][argument_name]
    tree = ast.parse(hint)
    node = tree.body[0].value
    arg_node = argument(argument_name, node)
    return arg_node


def generate_base_model_ast(classname="BaseModel", model_metadata=None):
    methods = model_metadata["methods"]
    func_nodes = []
    aliases = import_aliases("Any", "Dict", "List", "Literal", "Optional", "Tuple", "Union", "TypedDict")
    list_import_node = import_from_statement('typing', aliases, level=0)
    for method in methods:
        if methods[method]["module"] != BASE_MODULE:
            continue
        arg_nodes = []
        defaults = []
        for arg in methods[method]["args"]:
            name = arg['name']
            if name in BASE_ARGS:
                continue
            if arg['has_default']:
                default = infer_default(arg)
                default_node = constant(default)
                defaults.append(default_node)
            if method in BASE_TYPE_HINTS and name in BASE_TYPE_HINTS[method]:
                node = get_base_type_hint_node(method, name)
            else:
                node = argument(name, annotation=None)
            arg_nodes.append(node)
        args_node = function_arguments(arg_nodes, defaults)
        body = []
        # Get the docstring.
        if methods[method]["doc"] and isinstance(methods[method]["doc"], list):
            # Select an arbitrary docstring from the inheritance chain.
            doc = methods[method]["doc"][0]["doc"]
            docstring_node = docstring(doc)
            body.append(docstring_node)
        body.append(ellipsis_expression())
        function_node = function_definition(method, args_node, body, [])
        func_nodes.append(function_node)
    class_node = class_definition(classname, None, func_nodes)
    # Nodes expect location information like `lineno`.
    # `fix_missing_locations` will recalculate this information.
    module_node = module([list_import_node, class_node], [])
    new_tree = ast.fix_missing_locations(module_node)
    # new_tree = ast.fix_missing_locations(class_node)
    return new_tree


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


FieldStructure = Dict[str, Field]


def generate_record_ast(classname, fields: FieldStructure):
    """Generate a class that represents the return type of 'read' for a given model."""
    aliases = import_aliases("Any", "Dict", "List", "Literal", "Optional", "TypedDict", "Tuple", "Union")
    # Old: list_import_node = import_from_statement('typing', aliases, level=0)
    aliases = import_aliases("Any", "Dict", "List", "Literal", "Optional", "Tuple", "Union", "TypedDict")
    list_import_node = import_from_statement('typing', aliases, level=0)
    fields_definition = fields_type_definition(classname, fields.keys())
    
    annotation_nodes = []
    for field in fields:
        # Skip field names that are python keywords.
        # Example: 'global' on ir_rule.
        if keyword.iskeyword(field):
            continue
        data = fields[field]
        py_type = Z2P_TYPES[data['type']]
        node = variable_annotation(field, py_type)
        annotation_nodes.append(node)
    
    class_node = class_definition(classname, "TypedDict", annotation_nodes)
    module_node = module([list_import_node, fields_definition, class_node], [])
    new_tree = ast.fix_missing_locations(module_node)
    return new_tree


def generate_model_ast(classname, recordname, model_metadata):
    methods = model_metadata['methods']
    func_nodes = []
    alias = import_alias(recordname, None)
    fields_identifier = fields_variable_identifier(recordname)
    fields_alias = import_alias(fields_identifier, None)
    base_model_alias = import_alias("BaseModel", None)
    import_node = import_from_statement(recordname, [alias, fields_alias], level=1)
    base_import_node = import_from_statement('base', [base_model_alias], level=1)
    # Old: list_import_node = import_from_statement('typing', [import_alias("List", None)], level=0)
    aliases = import_aliases("Any", "Dict", "List", "Literal", "Optional", "Tuple", "Union")
    list_import_node = import_from_statement('typing', aliases, level=0)
    # __modelname__ = 'class.name'
    modelname_node = variable_assignment('__modelname__', constant(model_metadata['name']))
    func_nodes.append(modelname_node)
    for method in methods:
        if methods[method]["module"] == BASE_MODULE and method != "read":
            continue
        arg_nodes = []
        defaults = []
        for arg in methods[method]["args"]:
            name = arg['name']
            # Skip cr, uid, user.
            if name in BASE_ARGS:
                continue
            if arg['has_default']:
                default = infer_default(arg)
                default_node = constant(default)
                defaults.append(default_node)
            # Rather than doing this, specify a function in BASE_TYPE_HINTS
            # and then we can call some function here that creates the node if it's
            # a string or calls the function if its a callable.
            if method == "read" and name == "fields":
                fields_annotation = list_annotation(fields_identifier)
                node = argument(name, annotation=fields_annotation)
            elif method in BASE_TYPE_HINTS and name in BASE_TYPE_HINTS[method]:
                node = get_base_type_hint_node(method, name)
            else:
                node = argument(name, annotation=None)
            arg_nodes.append(node)
        args_node = function_arguments(arg_nodes, defaults)
        body = []
        # Get the docstring.
        if methods[method]["doc"] and isinstance(methods[method]["doc"], list):
            # Select an arbitrary docstring from the inheritance chain.
            doc = methods[method]["doc"][0]["doc"]
            docstring_node = docstring(doc)
            body.append(docstring_node)
        body.append(ellipsis_expression())
        returns = []
        if method == 'read':
            returns = list_annotation(recordname)
        function_node = function_definition(method, args_node, body, returns)
        func_nodes.append(function_node)
    class_node = class_definition(classname, 'BaseModel', func_nodes)
    module_node = module([list_import_node, import_node, base_import_node, class_node], [])
    # Nodes expect location information like `lineno`.
    # `fix_missing_locations` will recalculate this information.
    new_tree = ast.fix_missing_locations(module_node)
    return new_tree


# Z ==== E ====== R ====== P ====== | ======= Z ==== E ====== R ====== P ===== | ===== Z ==== E ====== R ====== P


def make_model_classname(identifier: str) -> str:
    """Convert sale.order to sale_order."""
    return identifier.replace(".", "_")


def make_read_model_classname(identifier: str) -> str:
    """Convert sale.order to sale_order_record."""
    new = identifier.replace(".", "_")
    return f"{new}_record"


def get_model_metadata(model):
    """Fetch model metadata."""
    metadata = model.model_metadata()
    return metadata


def get_all_model_metadata():
    arbitrary_obj = zerp.get('ir.model')
    compressed_data = arbitrary_obj.get_all_models_metadata_cached_json_compressed_b64()
    import lzma
    import base64
    decoded = base64.b64decode(compressed_data)
    decompressed = lzma.decompress(decoded)
    with open('all_metadata.json', 'w') as f:
        json.dump(json.loads(decompressed), f)
    return json.loads(decompressed)


# Declare at top or other file.
class ModelsResponse(TypedDict):
    id: int
    model: str


def get_models() -> List[ModelsResponse]:
    model_obj = zerp.get('ir.model')
    model_ids = model_obj.search([])
    return model_obj.read(
        model_ids,
        ['model']
    )


def write_model(tree: Union[ast.Module, ast.ClassDef], path: str) -> None:
    source = ast.unparse(tree)
    with open(path, "w") as f:
        f.write(source)


def display(model_name, current_count, total):
    s = "Loading: {0: <50} [{1}/{2}]".format(model_name, current_count, total)
    print(s, end="\r")
    # print(model_name, current_count, total)


def display_success(current_count, total):
    print("\n")
    s = f"{current_count}/{total} models successfully loaded."
    print(s)


if __name__ == "__main__":
    base_written = False
    model_metadata = get_all_model_metadata()
    n = len(model_metadata)
    count = 0
    for model_name in model_metadata:
        metadata = model_metadata[model_name]
        if metadata:
            count += 1
            display(metadata['name'], count, n)
        else:
            continue
        name = metadata['name']
        modelname = make_model_classname(name)
        recordname = make_read_model_classname(name)
        model_path = os.path.join(MODEL_DIRECTORY, modelname + ".py")
        record_path = os.path.join(MODEL_DIRECTORY, recordname + ".py")
        tree = generate_model_ast(modelname, recordname, metadata)
        record_tree = generate_record_ast(recordname, metadata['fields'])
        if not base_written:
            base_path = os.path.join(MODEL_DIRECTORY, 'base' + ".py")
            base_tree = generate_base_model_ast(model_metadata=metadata)
            write_model(base_tree, base_path)
        write_model(tree, model_path)
        write_model(record_tree, record_path)
    display_success(count, n)
