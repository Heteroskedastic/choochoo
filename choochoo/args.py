
from argparse import ArgumentParser
from genericpath import exists
from os import makedirs
from os.path import dirname, expanduser, realpath, normpath, relpath, join
from re import compile, sub
from typing import Mapping


PROGNAME = 'ch2'
COMMAND = 'command'

DIARY = 'diary'
INJURIES = 'injuries'
AIMS = 'aims'

ROOT = 'root'
DATABASE = 'database'
LOGS = 'logs'


def mm(name): return '--' + name


VARIABLE = compile(r'(.*(?:[^$]|^))\${(\w+)\}(.*)')


class NamespaceWithVariables(Mapping):

    def __init__(self, ns):
        self._dict = vars(ns)

    def __getitem__(self, name):
        value = self._dict[name]
        match = VARIABLE.match(value)
        while match:
            value = match.group(1) + self[match.group(2)] + match.group(3)
            match = VARIABLE.match(value)
        return sub(r'\$\$', '$', value)

    def path(self, name):
        path = expanduser(self[name])
        if relpath(path) and name != ROOT:
            path = join(self.path(ROOT), path)
        return realpath(normpath(path))

    def file(self, name):
        file = self.path(name)
        path = dirname(file)
        if not exists(path):
            makedirs(path)
        return file

    def dir(self, name):
        path = self.path(name)
        if not exists(path):
            makedirs(path)
        return path

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self.__dict__)


def parser():
    p = ArgumentParser()
    p.add_argument(mm(ROOT), action='store', default='~/.ch2', metavar='DIR',
                   help='The root directory for the default configuration')
    p.add_argument(mm(LOGS), action='store', default='logs', metavar='DIR',
                   help='The directory for logs')
    p.add_argument(mm(DATABASE), action='store', default='${root}/database.sql', metavar='FILE',
                   help='The database file')
    subparsers = p.add_subparsers()
    p_diary = subparsers.add_parser(DIARY,
                                    help='daily diary - see `%s %s -h` for more details' % (PROGNAME, DIARY))
    p_diary.set_defaults(command=DIARY)
    p_injuries = subparsers.add_parser(INJURIES,
                                       help='manage injury entries - see `%s %s -h` for more details' %
                                            (PROGNAME, INJURIES))
    p_injuries.set_defaults(command=INJURIES)
    p_aims = subparsers.add_parser(AIMS,
                                   help='manage aim entries - see `%s %s -h` for more details' % (PROGNAME, AIMS))
    p_aims.set_defaults(command=AIMS)
    return p
