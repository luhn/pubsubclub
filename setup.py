from setuptools import setup, find_packages

setup(
    name='pubsubclub',
    version='0.1.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
        ],
    },
    install_requires=[
        'autobahn <= 0.8.15',
        'twisted',
    ],
)
