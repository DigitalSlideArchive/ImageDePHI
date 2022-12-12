from setuptools import setup

setup(
    name='Image DePHI',
    install_requires=['tifftools'],
    entry_points={'console_scripts': ['imagedephi=imagedephi:main']},
)
