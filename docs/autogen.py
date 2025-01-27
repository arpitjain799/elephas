# -*- coding: utf-8 -*-

import re
import inspect
import os
import shutil
from pathlib import Path

from elephas import spark_model, ml_model
from elephas.parameter import client, server
from elephas.utils import functional_utils, rdd_utils, serialization
from elephas.ml import adapter as ml_adapter
from elephas.mllib import  adapter as mllib_adapter

PWD = Path(__file__).parent

PAGES = [
    {
        'page': 'models/spark-model.md',
        'classes': [
          spark_model.SparkModel
        ],
        'functions': [
          spark_model.load_spark_model
        ],
    },
    {
        'page': 'models/spark-mllib-model.md',
        'classes': [
          spark_model.SparkMLlibModel
        ],
        'functions': [
            spark_model.load_spark_model
        ],
    },
    {
        'page': 'models/spark-ml-model.md',
        'classes': [
            ml_model.ElephasEstimator,
            ml_model.ElephasTransformer
        ],
        'functions': [
            ml_model.load_ml_transformer,
            ml_model.load_ml_estimator
        ],
    },
    {
        'page': 'parameter/client.md',
        'classes': [
            client.BaseParameterClient,
            client.HttpClient
        ]
    },
    {
        'page': 'parameter/server.md',
        'classes': [
            server.BaseParameterServer,
            server.HttpServer
        ]
    },
    {
        'page': 'utils/functional_utils.md',
        'all_module_functions': [functional_utils],
    },
    {
        'page': 'utils/rdd_utils.md',
        'all_module_functions': [rdd_utils],
    },
    {
        'page': 'utils/serialization_utils.md',
        'all_module_functions': [serialization],
    },
    {
        'page': 'adapters/spark-ml.md',
        'all_module_functions': [ml_adapter],
    },
    {
        'page': 'adapters/spark-mllib.md',
        'all_module_functions': [mllib_adapter],
    },
]

ROOT = 'http://danielenricocahall.com/elephas'


def get_function_signature(function, method=True):
    wrapped = getattr(function, '_original_function', None)
    if wrapped is None:
        signature = inspect.signature(function)
    else:
        signature = inspect.signature(wrapped)
    parameters = [str(p[1]) for p in signature.parameters.items()]
    if method:
        parameters = parameters[1:]
    st = '%s.%s(' % (clean_module_name(function.__module__), function.__name__)

    for p in parameters:
        st += str(p) + ', '
    return st[:-2] + ')'


def get_class_signature(cls):
    try:
        class_signature = get_function_signature(cls.__init__)
        class_signature = class_signature.replace('__init__', cls.__name__)
    except (TypeError, AttributeError):
        # in case the class inherits from object and does not
        # define __init__
        class_signature = "{clean_module_name}.{cls_name}()".format(
            clean_module_name=clean_module_name(cls.__module__),
            cls_name=cls.__name__
        )
    return class_signature


def clean_module_name(name):
    assert name[:8] == 'elephas.', 'Invalid module name: %s' % name
    return name


def class_to_docs_link(cls):
    module_name = clean_module_name(cls.__module__)
    module_name = module_name[6:]
    link = ROOT + module_name.replace('.', '/') + '#' + cls.__name__.lower()
    return link


def class_to_source_link(cls):
    module_name = clean_module_name(cls.__module__)
    path = module_name.replace('.', '/')
    path += '.py'
    line = inspect.getsourcelines(cls)[-1]
    link = ('https://github.com/danielenricocahall/'
            'elephas/blob/master/' + path + '#L' + str(line))
    return '[[source]](' + link + ')'


def code_snippet(snippet):
    result = '```python\n'
    result += snippet + '\n'
    result += '```\n'
    return result


def count_leading_spaces(s):
    ws = re.search(r'\S', s)
    if ws:
        return ws.start()
    else:
        return 0


def process_list_block(docstring, starting_point, leading_spaces, marker):
    ending_point = docstring.find('\n\n', starting_point)
    block = docstring[starting_point:(None if ending_point == -1 else
                                      ending_point - 1)]
    # Place marker for later reinjection.
    docstring = docstring.replace(block, marker)
    lines = block.split('\n')
    # Remove the computed number of leading white spaces from each line.
    lines = [re.sub('^' + ' ' * leading_spaces, '', line) for line in lines]
    # Usually lines have at least 4 additional leading spaces.
    # These have to be removed, but first the list roots have to be detected.
    top_level_regex = r'^    ([^\s\\\(]+):(.*)'
    top_level_replacement = r'- __\1__:\2'
    lines = [re.sub(top_level_regex, top_level_replacement, line) for line in lines]
    # All the other lines get simply the 4 leading space (if present) removed
    lines = [re.sub(r'^    ', '', line) for line in lines]
    # Fix text lines after lists
    indent = 0
    text_block = False
    for i in range(len(lines)):
        line = lines[i]
        spaces = re.search(r'\S', line)
        if spaces:
            # If it is a list element
            if line[spaces.start()] == '-':
                indent = spaces.start() + 1
                if text_block:
                    text_block = False
                    lines[i] = '\n' + line
            elif spaces.start() < indent:
                text_block = True
                indent = spaces.start()
                lines[i] = '\n' + line
        else:
            text_block = False
            indent = 0
    block = '\n'.join(lines)
    return docstring, block


def process_docstring(docstring):
    # First, extract code blocks and process them.
    code_blocks = []
    if '```' in docstring:
        tmp = docstring[:]
        while '```' in tmp:
            tmp = tmp[tmp.find('```'):]
            index = tmp[3:].find('```') + 6
            snippet = tmp[:index]
            # Place marker in docstring for later reinjection.
            docstring = docstring.replace(
                snippet, '$CODE_BLOCK_%d' % len(code_blocks))
            snippet_lines = snippet.split('\n')
            # Remove leading spaces.
            num_leading_spaces = snippet_lines[-1].find('`')
            snippet_lines = ([snippet_lines[0]] +
                             [line[num_leading_spaces:]
                             for line in snippet_lines[1:]])
            # Most code snippets have 3 or 4 more leading spaces
            # on inner lines, but not all. Remove them.
            inner_lines = snippet_lines[1:-1]
            leading_spaces = None
            for line in inner_lines:
                if not line or line[0] == '\n':
                    continue
                spaces = count_leading_spaces(line)
                if leading_spaces is None:
                    leading_spaces = spaces
                if spaces < leading_spaces:
                    leading_spaces = spaces
            if leading_spaces:
                snippet_lines = ([snippet_lines[0]] +
                                 [line[leading_spaces:]
                                  for line in snippet_lines[1:-1]] +
                                 [snippet_lines[-1]])
            snippet = '\n'.join(snippet_lines)
            code_blocks.append(snippet)
            tmp = tmp[index:]

    # Format docstring lists.
    section_regex = r'\n( +)# (.*)\n'
    section_idx = re.search(section_regex, docstring)
    shift = 0
    sections = {}
    while section_idx and section_idx.group(2):
        anchor = section_idx.group(2)
        leading_spaces = len(section_idx.group(1))
        shift += section_idx.end()
        marker = '$' + anchor.replace(' ', '_') + '$'
        docstring, content = process_list_block(docstring,
                                                shift,
                                                leading_spaces,
                                                marker)
        sections[marker] = content
        section_idx = re.search(section_regex, docstring[shift:])

    # Format docstring section titles.
    docstring = re.sub(r'\n(\s+)# (.*)\n',
                       r'\n\1__\2__\n\n',
                       docstring)

    # Strip all remaining leading spaces.
    lines = docstring.split('\n')
    docstring = '\n'.join([line.lstrip(' ') for line in lines])

    # Reinject list blocks.
    for marker, content in sections.items():
        docstring = docstring.replace(marker, content)

    # Reinject code blocks.
    for i, code_block in enumerate(code_blocks):
        docstring = docstring.replace(
            '$CODE_BLOCK_%d' % i, code_block)
    return docstring


if os.path.exists(PWD/'sources'):
    print('Cleaning up existing sources directory.')
    shutil.rmtree(PWD/'sources')

print('Populating sources directory with templates.')
for subdir, dirs, fnames in os.walk(PWD/'templates'):
    for fname in fnames:
        new_subdir = subdir.replace(str(PWD/'templates'), str(PWD/'sources'))
        if not os.path.exists(PWD/new_subdir):
            os.makedirs(PWD/new_subdir)
        if fname[-3:] == '.md':
            fpath = str(PWD/os.path.join(subdir, fname))
            new_fpath = fpath.replace('templates', 'sources')
            shutil.copy(fpath, new_fpath)


def read_file(path):
    with open(path) as f:
        return f.read()


def collect_class_methods(cls, methods):
    if isinstance(methods, (list, tuple)):
        return [getattr(cls, m) if isinstance(m, str) else m for m in methods]
    methods = []
    for _, method in inspect.getmembers(cls, predicate=inspect.isroutine):
        methods.append(method)
    return methods


def render_function(function, method=True):
    subblocks = []
    signature = get_function_signature(function, method=method)
    if method:
        signature = signature.replace(
            clean_module_name(function.__module__) + '.', '')
    subblocks.append('### ' + function.__name__ + '\n')
    subblocks.append(code_snippet(signature))
    docstring = function.__doc__
    if docstring:
        subblocks.append(process_docstring(docstring))
    return '\n\n'.join(subblocks)


def read_page_data(page_data, type):
    assert type in ['classes', 'functions', 'methods']
    data = page_data.get(type, [])
    for module in page_data.get('all_module_{}'.format(type), []):
        module_data = []
        for name in dir(module):
            module_member = getattr(module, name)
            if (inspect.isclass(module_member) and type == 'classes' or
               inspect.isfunction(module_member) and type == 'functions'):
                instance = module_member
                if module.__name__ in instance.__module__:
                    if instance not in module_data:
                        module_data.append(instance)
        module_data.sort(key=lambda x: id(x))
        data += module_data
    return data


def replace_strikethroughs(index: str):
    strike_begin = True
    while index.find('~~') != -1:
        index = index.replace('~~', '<strike>' if strike_begin else '</strike>', 1)
        strike_begin = not strike_begin
    return index


if __name__ == '__main__':
    readme = read_file(PWD.parent/'README.md')
    index = read_file(PWD/'templates/index.md')
    index = index.replace('{{autogenerated}}', readme[readme.find('##'):])
    index = replace_strikethroughs(index)
    with open(PWD/'sources/index.md', 'w') as f:
        f.write(index)

    print('Generating Elephas docs')
    for page_data in PAGES:
        classes = read_page_data(page_data, 'classes')

        blocks = []
        for element in classes:
            if not isinstance(element, (list, tuple)):
                element = (element, [])
            cls = element[0]
            subblocks = []
            signature = get_class_signature(cls)
            subblocks.append('<span style="float:right;">' +
                             class_to_source_link(cls) + '</span>')
            if element[1]:
                subblocks.append('## ' + cls.__name__ + ' class\n')
            else:
                subblocks.append('### ' + cls.__name__ + '\n')
            subblocks.append(code_snippet(signature))
            docstring = cls.__doc__
            if docstring:
                subblocks.append(process_docstring(docstring))
            methods = collect_class_methods(cls, element[1])
            if methods:
                subblocks.append('\n---')
                subblocks.append('## ' + cls.__name__ + ' methods\n')
                subblocks.append('\n---\n'.join(
                    [render_function(method, method=True) for method in methods]))
            blocks.append('\n'.join(subblocks))

        methods = read_page_data(page_data, 'methods')

        for method in methods:
            blocks.append(render_function(method, method=True))

        functions = read_page_data(page_data, 'functions')

        for function in functions:
            blocks.append(render_function(function, method=False))

        if not blocks:
            raise RuntimeError('Found no content for page ' +
                               page_data['page'])

        mkdown = '\n----\n\n'.join(blocks)
        # save module page.
        # Either insert content into existing page,
        # or create page otherwise
        page_name = page_data['page']
        path = os.path.join(PWD/'sources', page_name)
        if os.path.exists(path):
            template = read_file(path)
            assert '{{autogenerated}}' in template, ('Template found for ' + path +
                                                     ' but missing {{autogenerated}}'
                                                     ' tag.')
            mkdown = template.replace('{{autogenerated}}', mkdown)
            print('...inserting autogenerated content into template:', path)
        else:
            print('...creating new page with autogenerated content:', path)
        subdir = os.path.dirname(path)
        if not os.path.exists(PWD/subdir):
            os.makedirs(PWD/subdir)
        with open(path, 'w') as f:
            f.write(mkdown)
