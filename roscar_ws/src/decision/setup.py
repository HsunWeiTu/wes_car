from setuptools import find_packages, setup

package_name = 'decision'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='wes',
    maintainer_email='wes@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'gesture_to_car_control_node = decision.gesture_to_car_control_node:main',
            'joy_to_car_control_node = decision.joy_to_car_control_node:main',
        ],
    },
)
