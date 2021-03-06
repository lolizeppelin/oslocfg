# Copyright 2012 SINA Corporation
# Copyright 2014 Cisco Systems, Inc.
# All Rights Reserved.
# Copyright 2014 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Sample configuration generator

Tool for generating a sample configuration file. See
../doc/source/generator.rst for details.

.. versionadded:: 1.4
"""

import collections
import logging
import operator
import sys
import textwrap

import six
import traceback

from oslocfg import cfg

LOG = logging.getLogger(__name__)

_generator_opts = [
    cfg.StrOpt('output-file',
               help='Path of the file to write to. Defaults to stdout.'),
    cfg.IntOpt('wrap-width',
               default=70,
               help='The maximum length of help lines.'),
    cfg.MultiStrOpt('opts',
                    required=True,
                    default=[],
                    help='Function query for options'),
    cfg.MultiStrOpt('updates',
                    default=[],
                    help='Function reset default value of opts'),
]


def import_class(import_str):
    """Returns a class from a string including module and class.

    .. versionadded:: 0.3
    """
    mod_str, _sep, class_str = import_str.rpartition('.')
    __import__(mod_str)
    try:
        return getattr(sys.modules[mod_str], class_str)
    except AttributeError:
        raise ImportError('Class %s cannot be found (%s)' %
                          (class_str,
                           traceback.format_exception(*sys.exc_info())))


def register_cli_opts(conf):
    """Register the formatter's CLI options with a ConfigOpts instance.

    Note, this must be done before the ConfigOpts instance is called to parse
    the configuration.

    :param conf: a ConfigOpts instance
    :raises: DuplicateOptError, ArgsAlreadyParsedError
    """
    conf.register_cli_opts(_generator_opts)


def _format_defaults(opt):
    """Return a list of formatted default values."""
    if isinstance(opt, cfg.MultiStrOpt):
        if opt.sample_default is not None:
            defaults = opt.sample_default
        elif not opt.default:
            defaults = ['']
        else:
            defaults = opt.default
    else:
        if opt.sample_default is not None:
            default_str = str(opt.sample_default)
        elif opt.default is None:
            default_str = '<None>'
        elif (isinstance(opt, cfg.StrOpt) or
              isinstance(opt, cfg.IPOpt) or
              isinstance(opt, cfg.HostnameOpt)):
            default_str = opt.default
        elif isinstance(opt, cfg.BoolOpt):
            default_str = str(opt.default).lower()
        elif isinstance(opt, (cfg.IntOpt, cfg.FloatOpt,
                              cfg.PortOpt)):
            default_str = str(opt.default)
        elif isinstance(opt, (cfg.ListOpt, cfg._ConfigFileOpt,
                              cfg._ConfigDirOpt)):
            default_str = ','.join(opt.default)
        elif isinstance(opt, cfg.DictOpt):
            sorted_items = sorted(opt.default.items(),
                                  key=operator.itemgetter(0))
            default_str = ','.join(['%s:%s' % i for i in sorted_items])
        else:
            LOG.warning('Unknown option type: %s', repr(opt))
            default_str = str(opt.default)
        defaults = [default_str]

    results = []
    for default_str in defaults:
        if default_str.strip() != default_str:
            default_str = '"%s"' % default_str
        results.append(default_str)
    return results


class _OptFormatter(object):

    """Format configuration option descriptions to a file."""

    def __init__(self, output_file=None, wrap_width=70):
        """Construct an OptFormatter object.

        :param output_file: a writeable file object
        :param wrap_width: The maximum length of help lines, 0 to not wrap
        """
        self.output_file = output_file or sys.stdout
        self.wrap_width = wrap_width

    def _format_help(self, help_text):
        """Format the help for a group or option to the output file.

        :param help_text: The text of the help string
        """
        if self.wrap_width is not None and self.wrap_width > 0:
            wrapped = ""
            for line in help_text.splitlines():
                text = "\n".join(textwrap.wrap(line, self.wrap_width,
                                               initial_indent='# ',
                                               subsequent_indent='# ',
                                               break_long_words=False,
                                               replace_whitespace=False))
                wrapped += "#" if text == "" else text
                wrapped += "\n"
            lines = [wrapped]
        else:
            lines = ['# ' + help_text + '\n']
        return lines

    def _get_choice_text(self, choice):
        if choice is None:
            return '<None>'
        elif choice == '':
            return "''"
        return six.text_type(choice)

    def format_group(self, group_or_groupname):
        """Format the description of a group header to the output file

        :param group_or_groupname: a cfg.OptGroup instance or a name of group
        """
        if isinstance(group_or_groupname, cfg.OptGroup):
            group = group_or_groupname
            lines = ['[%s]\n' % group.name]
            if group.help:
                lines += self._format_help(group.help)
        else:
            groupname = group_or_groupname
            lines = ['[%s]\n' % groupname]
        self.writelines(lines)

    def format(self, opt):
        """Format a description of an option to the output file.

        :param opt: a cfg.Opt instance
        """
        if not opt.help:
            LOG.warning('"%s" is missing a help string', opt.dest)

        option_type = getattr(opt, 'type', None)
        opt_type = getattr(option_type, 'type_name', 'unknown value')

        if opt.help:
            help_text = u'%s (%s)' % (opt.help,
                                      opt_type)
        else:
            help_text = u'(%s)' % opt_type
        lines = self._format_help(help_text)

        if getattr(opt.type, 'min', None) is not None:
            lines.append('# Minimum value: %d\n' % opt.type.min)

        if getattr(opt.type, 'max', None) is not None:
            lines.append('# Maximum value: %d\n' % opt.type.max)

        if getattr(opt.type, 'choices', None):
            choices_text = ', '.join([self._get_choice_text(choice)
                                      for choice in opt.type.choices])
            lines.append('# Allowed values: %s\n' % choices_text)

        try:
            if opt.mutable:
                lines.append(
                    '# Note: This option can be changed without restarting.\n'
                )
        except AttributeError as err:
            # NOTE(dhellmann): keystoneauth defines its own Opt class,
            # and neutron (at least) returns instances of those
            # classes instead of oslo_config Opt instances. The new
            # mutable attribute is the first property where the API
            # isn't supported in the external class, so we can use
            # this failure to emit a warning. See
            # https://bugs.launchpad.net/keystoneauth/+bug/1548433 for
            # more details.
            import warnings
            if not isinstance(cfg.Opt, opt):
                warnings.warn(
                    'Incompatible option class for %s (%r): %s' %
                    (opt.dest, opt.__class__, err),
                )
            else:
                warnings.warn('Failed to fully format sample for %s: %s' %
                              (opt.dest, err))

        for d in opt.deprecated_opts:
            lines.append('# Deprecated group/name - [%s]/%s\n' %
                         (d.group or 'DEFAULT', d.name or opt.dest))

        if opt.deprecated_for_removal:
            lines.append(
                '# This option is deprecated for removal.\n'
                '# Its value may be silently ignored in the future.\n')
            if opt.deprecated_reason:
                lines.extend(
                    self._format_help('Reason: ' + opt.deprecated_reason))
        if hasattr(opt.type, 'format_defaults'):
            defaults = opt.type.format_defaults(opt.default,
                                                opt.sample_default)
        else:
            LOG.debug(
                "The type for option %(name)s which is %(type)s is not a "
                "subclass of types.ConfigType and doesn't provide a "
                "'format_defaults' method. A default formatter is not "
                "available so the best-effort formatter will be used.",
                {'type': opt.type, 'name': opt.name})
            defaults = _format_defaults(opt)
        for default_str in defaults:
            if default_str:
                default_str = ' ' + default_str
            lines.append('#%s =%s\n' % (opt.dest, default_str))

        self.writelines(lines)

    def write(self, s):
        """Write an arbitrary string to the output file.

        :param s: an arbitrary string
        """
        self.output_file.write(s)

    def writelines(self, l):
        """Write an arbitrary sequence of strings to the output file.

        :param l: a list of arbitrary strings
        """
        self.output_file.writelines(l)


def _cleanup_opts(read_opts):
    """Cleanup duplicate options in namespace groups

    Return a structure which removes duplicate options from a namespace group.
    NOTE:(rbradfor) This does not remove duplicated options from repeating
    groups in different namespaces:

    :param read_opts: a list (namespace, [(group, [opt_1, opt_2])]) tuples
    :returns: a list of (namespace, [(group, [opt_1, opt_2])]) tuples
    """

    # OrderedDict is used specifically in the three levels to maintain the
    # source order of namespace/group/opt values
    clean = collections.OrderedDict()
    for namespace, listing in read_opts:
        if namespace not in clean:
            clean[namespace] = collections.OrderedDict()

        for group, opts in listing:
            if group not in clean[namespace]:
                clean[namespace][group] = collections.OrderedDict()
            for opt in opts:
                clean[namespace][group][opt.dest] = opt

    # recreate the list of (namespace, [(group, [opt_1, opt_2])]) tuples
    # from the cleaned structure.
    cleaned_opts = [
        (namespace, [(group, list(clean[namespace][group].values()))
                     for group in clean[namespace]])
        for namespace in clean
    ]

    return cleaned_opts


def _get_raw_opts_loaders(namespaces):
    """List the options available via the given namespaces.

    :param namespaces: a list of namespaces registered under 'oslo.config.opts'
    :returns: a list of (namespace, [(group, [opt_1, opt_2])]) tuples
                                    # (name, [(group, opts())])
    """
    _map = []
    groups = {}
    for namespace in namespaces:
        name, cls = namespace.split(":")
        if name.lower() == 'default':
            name = 'DEFAULT'
            group = None
        else:
            if name not in groups:
                groups[name] = cfg.OptGroup(name)
            group = groups[name]
        func = import_class(cls)
        _map.append((name, [(group, func())]))
    return _map


def _update_defaults(namespaces, updates):
    """Let application hooks update defaults inside libraries."""
    names = set()
    for namespace in namespaces:
        name, cls = namespace.split(":")
        names.add(name)
    for update in updates:
        name, cls = update.split(":")
        func = import_class(cls)
        if name in names:
            func()
            names.remove(name)


def _list_opts(namespaces, updates):
    """List the options available via the given namespaces.

    Duplicate options from a namespace are removed.

    :param namespaces: a list of namespaces registered under 'oslo.config.opts'
    :returns: a list of (namespace, [(group, [opt_1, opt_2])]) tuples
    """
    # Load the functions to get the options.
    loaders = _get_raw_opts_loaders(namespaces)
    opts = loaders
    _update_defaults(namespaces, updates)

    # Update defaults, which might change global settings in library
    # modules.
    # Ask for the option definitions. At this point any global default
    # changes made by the updaters should be in effect.
    # opts = [
    #     (namespace, loader())
    #     for namespace, loader in loaders
    # ]
    return _cleanup_opts(opts)


def on_load_failure_callback(*args, **kwargs):
    raise RuntimeError("on load failure callback")


def _output_opts(f, group, namespaces):
    f.format_group(group)
    for (namespace, opts) in sorted(namespaces,
                                    key=operator.itemgetter(0)):
        f.write('\n#\n# From %s\n#\n' % namespace)
        for opt in opts:
            f.write('\n')
            try:
                f.format(opt)
            except Exception as err:
                f.write('# Warning: Failed to format sample for %s\n' %
                        (opt.dest,))
                f.write('# %s\n' % (err,))


def _get_group_name(item):
    group = item[0]
    # The keys of the groups dictionary could be an OptGroup. Otherwise the
    # help text of an OptGroup wouldn't be part of the generated sample
    # file. It could also be just a plain group name without any further
    # attributes. That's the reason why we have to differentiate here.
    return group.name if isinstance(group, cfg.OptGroup) else group


def _get_groups(conf_ns):
    groups = {'DEFAULT': []}
    for namespace, listing in conf_ns:
        for group, opts in listing:
            if not opts:
                continue
            namespaces = groups.setdefault(group or 'DEFAULT', [])
            namespaces.append((namespace, opts))
    return groups


def generate(conf):
    """Generate a sample config file.

    List all of the options available via the namespaces specified in the given
    configuration and write a description of them to the specified output file.

    :param conf: a ConfigOpts instance containing the generator's configuration
    """
    conf.register_opts(_generator_opts)

    output_file = (open(conf.output_file, 'w')
                   if conf.output_file else sys.stdout)

    formatter = _OptFormatter(output_file=output_file,
                              wrap_width=conf.wrap_width)

    groups = _get_groups(_list_opts(conf.opts, conf.updates))

    # Output the "DEFAULT" section as the very first section
    _output_opts(formatter, 'DEFAULT', groups.pop('DEFAULT'))

    # output all other config sections with groups in alphabetical order
    for group, namespaces in sorted(groups.items(), key=_get_group_name):
        formatter.write('\n\n')
        _output_opts(formatter, group, namespaces)


def make(cf):
    logging.basicConfig(level=logging.INFO)
    conf = cfg.ConfigOpts()
    register_cli_opts(conf)
    conf(default_config_files=[cf, ])
    generate(conf)
