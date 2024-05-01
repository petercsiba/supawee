from setuptools import setup, find_packages

setup(
    name='supawee',
    version='0.1.0',
    author='Peter Csiba',
    author_email='me@petercsiba.com',
    description='A Peewee integration for Supabase with programmatic model generation',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/petercsiba/supawee',
    packages=find_packages(),
    # TODO(P2, Devx): Ideally automate this from requirements/common.txt
    # https://chat.openai.com/share/6d52958f-b71d-427a-ae01-9c9b1c8df140
    install_requires=[
        'black',
        'psycopg2>=2.0',
        'peewee>=3.0',
    ],
    entry_points={
        'console_scripts': [
            'supawee=supawee.generate_models:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.7',  # Minimum Python version requirement
)