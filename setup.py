from setuptools import setup, find_packages

setup(
    name='kang-sensor', 
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'rich',
        'google-generativeai'
    ],
    entry_points={
        'console_scripts': [
            'kang-sensor=kang_sensor.app:main', 
        ],
    },
)
