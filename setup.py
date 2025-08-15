from setuptools import setup

APP = ['Hunt-Analizer.py']
DATA_FILES = ['tibia_hunts.db']
OPTIONS = {'argv_emulation': True}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

