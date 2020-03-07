from setuptools import setup, find_packages
#from distutils import setup, find_packages

setup(
    name = "morphometrix",
    version = "1.0.2",
    description="A GUI for photogrammetry",
    author = "Walter Torres",
    author_email = "walter.torres@duke.edu",
    license='MIT',
    url = "https://github.com/wingtorres/morphometrix/",
    entry_points={
        'gui_scripts': [
            'morphometrix = morphometrix.__main__:main'
        ]
    },
#    scripts=['morphometrix/morphometrix.py'],
    packages = ['morphometrix']
#    packages= find_packages()
)