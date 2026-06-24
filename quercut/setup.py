from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='quercut',
    version='0.1.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='Гильотинный раскрой листовых материалов',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/quercut',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Manufacturing',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.10',
    install_requires=[
        'setuptools>=68.0.0',
    ],
)