import nox
import os
import glob

@nox.session()
def build(session):
    session.run("pdm", "build")

@nox.session(python=['/opt/pypy3/bin/pypy3.10', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13' ])
def tests(session):
    session.install("pytest")

    # Find the whl packages. We're going to sort by newest to oldest
    # so for testing we can install the freshest copy
    package_files = sorted(
                        glob.glob("dist/izaber_wamp_zerp-*.whl"),
                        key=os.path.getmtime,
                        reverse=True
                    )

    if not package_files:
        raise FileNotFoundError("No izaber_wamp_zerp-VERSION.whl package found in the 'dist' directory.")

    # Install the built package
    session.install(package_files[0])

    # Run tests
    session.run("pytest", "--log-cli-level=WARN", "-s")
