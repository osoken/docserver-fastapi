from setuptools import setup

from docserver import (
    __author__,
    __description__,
    __email__,
    __package_name__,
    __version__,
)

setup(
    name=__package_name__,
    version=__version__,
    author=__author__,
    author_email=__email__,
    license="MIT",
    url="https://github.com/osoken/docserver-fastapi",
    description=__description__,
    long_description=__description__,
    packages=[__package_name__],
    install_requires=[
        "alembic[tz]",
        "fastapi",
        "SQLAlchemy",
        "shortuuid",
        "pyhumps",
        "python-dotenv",
        "pydantic[email]",
        "uvicorn",
        "uvloop",
        "httptools",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
    ],
    extras_require={
        "dev": [
            "flake8",
            "pytest",
            "pytest-mock",
            "freezegun",
            "black",
            "mypy==0.931",
            "tox",
            "isort",
            "psycopg2-binary",
            "requests",
            "pydantic-factories",
            "factory_boy",
        ],
        "prod": ["psycopg2"],
    },
)
