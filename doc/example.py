from oslocfg import cfg


# CONF is global var
CONF = cfg.CONF

_cli_opts = [
    cfg.StrOpt('name',
               required=True,
               help='Gopcdn resource for objfile'),
]


_opts = [
    cfg.IntOpt('objfile_resource',
               default=0,
               help='Gopcdn resource for objfile'),
    cfg.IntOpt('package_resource',
               default=0,
               help='Gopcdn resource for packages files'),
]


def list_opts():
    return _cli_opts + _opts


group = cfg.OptGroup(name="test", title='group for test')

# cli options  register before CONF init
CONF.register_cli_opts(_cli_opts)

# CONF init
CONF(args=['--config-dir', '/etc/oslocfg-dir'],
     project=group.name,
     default_config_files=['/etc/oclocfg.conf'])

CONF.register_opts(_opts, group)

