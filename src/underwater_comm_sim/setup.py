from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'underwater_comm_sim'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='wei1367',
    maintainer_email='wei1367@todo.todo',
    description='Underwater acoustic communication simulation package',
    license='Apache-2.0',
    scripts=glob('scripts/*.py'),
)
