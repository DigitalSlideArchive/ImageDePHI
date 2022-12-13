from setuptools import setup

setup(
    name='ImageDePHI',
    install_requires=['tifftools'],
    entry_points={'console_scripts': ['imagedephi=imagedephi:main']},
)
