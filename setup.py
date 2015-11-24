from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
#import py2exe

setup(
    name = "Yombo",
    version = "0.10.0",
    description = "Yombo Gateway Software",
    author='Mitch Schwenk',
    author_email='mitch-gwy@yombo.net',
    url='https://yombo.net/',
#    package_dir= {'Yombo' : 'src/Yombo'},
#    packages=['Yombo', 'yombo'],
    packages=['yombo'],
    cmdclass = {'build_ext': build_ext},
    py_modules = [
                  'yombo/core/auth',
                  'yombo/core/component',
                  'yombo/core/db',
                  'yombo/core/exceptions',
                  'yombo/core/gwservice',
                  'yombo/core/helpers',
                  'yombo/core/log',
                  'yombo/core/voicecmd',
#                  'yombo/lib/configurationupdate',
                  'yombo/lib/controller',
                  'yombo/lib/loader',
                  'yombo/lib/startup',
                  ],

    ext_modules =  [
                    Extension("yombo.core.fuzzysearch", ["yombo/core/fuzzysearch.pyx"], extra_link_args=['-s']),
                    Extension("yombo.core.message", ["yombo/core/message.pyx"], extra_link_args=['-s']),
                    Extension("yombo.core.sqldict", ["yombo/core/sqldict.pyx"], extra_link_args=['-s']),
#                    Extension("yombo.core.voicecmd", ["yombo/core/voicecmd.pyx"], extra_link_args=['-s']),

                    Extension("yombo.lib.configuration", ["yombo/lib/configuration.pyx"], extra_link_args=['-s']),
                    Extension("yombo.lib.configurationupdate", ["yombo/lib/configurationupdate.pyx"], extra_link_args=['-s']),
                    Extension("yombo.lib.commands", ["yombo/lib/commands.pyx"], extra_link_args=['-s']),
                    Extension("yombo.lib.devices", ["yombo/lib/devices.pyx"], extra_link_args=['-s']),
                    Extension("yombo.lib.downloadmodules", ["yombo/lib/downloadmodules.pyx"], extra_link_args=['-s']),
                    Extension("yombo.lib.gatewaycontrol", ["yombo/lib/gatewaycontrol.pyx"], extra_link_args=['-s']),
#                    Extension("yombo.lib.gatewaydata", ["yombo/lib/gatewaydata.pyx"], extra_link_args=['-s']),
                    Extension("yombo.lib.times", ["yombo/lib/times.pyx"], extra_link_args=['-s']),
                   ],
    data_files = [
                  ('yombo', ['yombod', 'yombo.tac', 'LICENSE', 'README']),
                  ('/etc', ['yombo.ini']),
                 ],
)
