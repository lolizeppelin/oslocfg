from oslocfg import cfg


# CONF is global var
CONF = cfg.CONF

_cli_opts = [
    cfg.StrOpt('name',
               short='n',
               required=True,
               help='Gopcdn resource for objfile'),
]

CONF.register_cli_opts(_cli_opts)
CONF()