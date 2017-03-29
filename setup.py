import setuptools

from version import __version__ as version


setuptools.setup(
    name='rtv',
    version=version,
    description='A simple terminal viewer for Reddit (Reddit Terminal Viewer)',
    long_description=open('README.rst').read(),
    url='https://github.com/michael-lazar/rtv',
    author='Michael Lazar',
    author_email='lazar.michael22@gmail.com',
    license='MIT',
    keywords='reddit terminal praw curses',
    packages=[
        'rtv',
        'rtv.packages',
        'rtv.packages.praw',
        ],
    package_data={
        'rtv': ['templates/*'],
        'rtv.packages.praw': ['praw.ini'],
        },
    data_files=[("share/man/man1", ["rtv.1"])],
    install_requires=[
        'beautifulsoup4',
        'decorator',
        'kitchen',
        'mailcap-fix',
        # For info on why this is pinned, see https://github.com/michael-lazar/rtv/issues/325
        'requests >=2.4.0',
        'six',
        ],
    entry_points={'console_scripts': ['rtv=rtv.__main__:main']},
    classifiers=[
        'Intended Audience :: End Users/Desktop',
        'Environment :: Console :: Curses',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Topic :: Terminals',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Message Boards',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
        ],
)
