from paver.tasks import task, needs, environment, cmdopts
from paver.runtime import sh, log, dry
from paver.path import path
from paver.options import Bunch
from paver import setuputils

from paver.release import setup_meta

import paver.doctools
import paver.virtual
import paver.setuputils

paver.setuputils.install_distutils_tasks()

options = environment.options

options(
    setup = setup_meta,
    minilib=Bunch(
        extra_files=['doctools', 'virtual']
    ),
    sphinx=Bunch(
        builddir="build",
        sourcedir="source"
    ),
    virtualenv=Bunch(
        packages_to_install=["nose", "sphinx", "docutils", "virtualenv"],
        install_paver=False,
        script_name='bootstrap.py',
        paver_command_line=None
    ),
    cog=Bunch(
        includedir="docs/samples",
        beginspec="<==",
        endspec="==>",
        endoutput="<==end==>"
    ),
    deploy=Bunch(
        deploydir="blueskyonmars.com/projects/paver"
    )
)

# not only does paver bootstrap itself, but it should work even with just 
# distutils
if setuputils.has_setuptools:
    old_sdist = "setuptools.command.sdist"
    options.setup.update(dict(
        install_requires=[],
        test_suite='nose.collector',
        zip_safe=False,
        entry_points="""
[console_scripts]
paver = paver.tasks:main
"""
    ))
else:
    old_sdist = "distutils.command.sdist"
    options.setup.scripts = ['scripts/paver']

options.setup.package_data=setuputils.find_package_data("paver", package="paver",
                                                only_in_packages=False)

if paver.doctools.has_sphinx:
    @task
    @needs(['cog', 'paver.doctools.html'])
    def html():
        """Build Paver's documentation and install it into paver/docs"""
        builtdocs = path("docs") / options.sphinx.builddir / "html"
        destdir = path("paver") / "docs"
        destdir.rmtree()
        builtdocs.move(destdir)
    
    @task
    @needs(['html', "minilib", "generate_setup", old_sdist])
    def sdist():
        """Builds the documentation and the tarball."""
        pass

if paver.virtual.has_virtualenv:
    @task
    def bootstrap():
        """Build a virtualenv bootstrap for developing paver."""
        # we have to pull some private api shenanigans that normal people don't
        # because we're bootstrapping paver itself.
        paver.virtual._create_bootstrap(options.script_name,
                              options.packages_to_install,
                              options.paver_command_line,
                              options.install_paver,
                              more_text="""    subprocess.call([join("""
                              """bin_dir, 'python'), '-c', """
                              """'import sys; sys.path.append("."); """
                              """import paver.command; paver.command.main()', """
                              """'develop'])""")
    
@task
def clean():
    """Cleans up this paver directory. Removes the virtualenv traces and
    the build directory."""
    path("build").rmtree()
    path("bin").rmtree()
    path("lib").rmtree()
    path(".Python").remove()
    
@task
@needs("uncog")
def commit():
    """Removes the generated code from the docs and then commits to bzr."""
    sh("bzr commit")
    
@task
@cmdopts([("username=", "u", "Username for remote server"),
          ("server=", "s", "Server to deploy to")])
def deploy():
    """Copy the Paver website up."""
    htmlfiles = path("paver/docs")
    command = "rsync -avz -e ssh %s/ %s@%s:%s/" % \
            (htmlfiles, options.username, options.server,
             options.deploydir)
    sh(command)
    