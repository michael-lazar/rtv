from setuptools import setup
#python setup.py develop --user
#python setup.py develop --user --uninstall

setup(
    name='rtv',
    version='1.0a4',
    description='A simple terminal viewer for Reddit (Reddit Terminal Viewer)',
    long_description=(
        '**Reddit Terminal Viewer (RTV)** is a lightweight browser '
        'for Reddit (www.reddit.com) built into a terminal window. '
        'RTV is built in Python and utilizes the **curses** library. ' 
        'It is compatible with a large range of terminal emulators on '
        'Linux and OSX systems.'),
    url='https://github.com/michael-lazar/rtv',
    author='Michael Lazar',
    author_email='lazar.michael22@gmail.com',
    license='MIT',
    keywords='reddit terminal praw curses',
    packages=['rtv'],
    install_requires=['praw', 'six'],
    entry_points={'console_scripts': ['rtv=rtv.main:main']},
    classifiers=[
        'Intended Audience :: End Users/Desktop',
        'Environment :: Console :: Curses',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Terminals',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Message Boards',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
        ],
)
