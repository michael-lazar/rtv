from setuptools import setup
from version import __version__ as version

import sys

requirements = ['tornado', 'praw>=3.1.0', 'six', 'requests', 'kitchen']

# Python 2: add required concurrent.futures backport from Python 3.2
if sys.version_info.major <= 2:
    requirements.append('futures')

setup(
    name='rtv',
    version=version,
    description='A simple terminal viewer for Reddit (Reddit Terminal Viewer)',
    long_description=open('README.rst').read(),
    url='https://github.com/michael-lazar/rtv',
    author='Michael Lazar',
    author_email='lazar.michael22@gmail.com',
    license='MIT',
    keywords='reddit terminal praw curses',
    packages=['rtv'],
    include_package_data=True,
<<<<<<< HEAD
    data_files=[("share/man/man1", ["rtv.1"])],
    install_requires=['praw>=3.1.0', 'six', 'requests', 'kitchen'],
=======
    install_requires=requirements,
>>>>>>> 28d17b28d0840f75386586686897e9316378150e
    entry_points={'console_scripts': ['rtv=rtv.__main__:main']},
    classifiers=[
        'Intended Audience :: End Users/Desktop',
        'Environment :: Console :: Curses',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3',
        'Topic :: Terminals',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Message Boards',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
        ],
)
