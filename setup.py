import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="synapse-uploader",
    version="0.0.beta2",
    author="Patrick Stout",
    author_email="pstout@prevagroup.com",
    license="Apache2",
    description="Synapse upload utility.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ki-tools/synapse_uploader",
    packages=setuptools.find_packages(exclude=['tests*']),
    classifiers=(
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    entry_points={
        'console_scripts': [
            "synapse-uploader = src.cli:main"
        ]
    },
    install_requires=[
        'synapseclient==1.9.0',
    ]
)
