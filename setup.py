from setuptools import setup
import os
#python setup.py develop --user
#python setup.py develop --user --uninstall


def read(*paths):
    """ read files """
    with open(os.path.join(*paths), 'r') as filename:
        return filename.read()

setup(
    name='rtv',
    version='1.0a7',
    description='A simple terminal viewer for Reddit (Reddit Terminal Viewer)',
    long_description=(read('README.rst')),
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
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Terminals',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Message Boards',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
        ],
)
