# -*- coding: utf-8 -*-
"""
    jinja2.testsuite.conftest
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Configuration and Fixtures for the tests

    :copyright: (c) 2017 by the Jinja Team.
    :license: BSD, see LICENSE for more details.
"""
import pytest
import os

from jinja2 import loaders
from jinja2.utils import have_async_gen
from jinja2 import Environment


def pytest_ignore_collect(path, config):
    if 'async' in path.basename and not have_async_gen:
        return True
    return False


@pytest.fixture
def env():
    '''returns a new environment.
    '''
    return Environment()


@pytest.fixture
def dict_loader():
    '''returns DictLoader
    '''
    return loaders.DictLoader({
        'justdict.html':        'FOO'
    })


@pytest.fixture
def package_loader():
    '''returns PackageLoader initialized from templates
    '''
    return loaders.PackageLoader('res', 'templates')

@pytest.fixture
def importlib_resource_loader():
    '''returns ImportLibResourceLoader initialized from templates
    '''
    return loaders.ImportLibResourceLoader('res.templates')


@pytest.fixture
def filesystem_loader():
    '''returns FileSystemLoader initialized to res/templates directory
    '''
    here = os.path.dirname(os.path.abspath(__file__)) + '/res/templates'
    for dirpath, dirnames, filenames in os.walk(here):
        for filename in filenames:
            if filename.endswith('.pyc'):
                os.remove(os.path.join(dirpath, filename))
    return loaders.FileSystemLoader(here)


@pytest.fixture
def function_loader():
    '''returns a FunctionLoader
    '''
    return loaders.FunctionLoader({'justfunction.html': 'FOO'}.get)


@pytest.fixture
def choice_loader(dict_loader, package_loader):
    '''returns a ChoiceLoader
    '''
    return loaders.ChoiceLoader([dict_loader, package_loader])


@pytest.fixture
def prefix_loader(filesystem_loader, dict_loader):
    '''returns a PrefixLoader
    '''
    return loaders.PrefixLoader({
        'a':        filesystem_loader,
        'b':        dict_loader
    })
