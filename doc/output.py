import os
from oslocfg import generator

pwd = os.path.split(__file__)[0]
os.chdir(pwd)

generator.make(cf='output.conf')