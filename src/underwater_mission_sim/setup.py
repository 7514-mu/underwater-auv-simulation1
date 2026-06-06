from setuptools import setup
from glob import glob

setup(
    name='underwater_mission_sim',
    version='0.1.0',
    packages=[],
    py_modules=[],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/underwater_mission_sim']),
        ('share/underwater_mission_sim', ['package.xml']),
        ('share/underwater_mission_sim/launch', glob('launch/*.py')),
        ('share/underwater_mission_sim/config', glob('config/*.yaml')),
    ],
    scripts=[
        'scripts/acoustic_comm_simulator.py',
        'scripts/underwater_detector.py',
        'scripts/underwater_identifier.py',
        'scripts/underwater_tracker.py',
    ],
    install_requires=['setuptools'],
    zip_safe=True,
)
