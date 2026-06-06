from setuptools import setup

package_name = 'uuv_fault_injection'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/fault_injection.launch.py']),
        ('share/' + package_name + '/config', ['config/fault_scenarios.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@todo.todo',
    description='AUV Fault Injection System for UUV Simulator',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'fault_injector = uuv_fault_injection.scripts.fault_injector:main',
        ],
    },
)
