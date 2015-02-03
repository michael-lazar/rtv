from setuptools import setup

setup(
    name='rtv',
    version='1.0a1',
    description='A simple terminal viewer for Reddit (Reddit Terminal Viewer)',
    url='http://TODO',
    author='Michael Lazar',
    author_email='lazar.michael22@gmail.com',
    license='MIT',
    keywords='reddit terminal praw',
    packages=['rtv'],
    install_requires=['praw'],
    entry_points={'console_scripts': ['rtv=rtv:main']}
)

#python setup.py develop --user