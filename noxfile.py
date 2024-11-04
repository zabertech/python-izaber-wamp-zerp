import nox

@nox.session()
def build(session):
    session.run("pdm", "build", )

@nox.session(python=['/opt/pypy3/bin/pypy3', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13' ])
def tests(session):
    session.install("pytest")
    session.install(".")

    session.run("pytest", "--log-cli-level=WARN", "-s")
