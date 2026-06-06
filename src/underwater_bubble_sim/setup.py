from setuptools import setup
import os
from glob import glob

setup(
    name='underwater_bubble_sim',
    version='0.1.0',
    packages=[],
    py_modules=[],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/underwater_bubble_sim']),
        ('share/underwater_bubble_sim', ['package.xml']),
        ('share/underwater_bubble_sim/launch', glob('launch/*.py')),
        ('share/underwater_bubble_sim/config', glob('config/*.yaml')),
    ],
    scripts=[
        'scripts/bubble_generator.py',
        'scripts/bubble_image_processor.py',
        'scripts/bubble_dynamics.py',
    ],
    install_requires=['setuptools'],
    zip_safe=True,
)
