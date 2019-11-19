import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="synapse-uploader",
    version="0.0.1",
    author="Patrick Stout",
    author_email="pstout@prevagroup.com",
    license="Apache2",
    description="Utility to upload a directory and files to Synapse.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ki-tools/synapse_uploader",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    classifiers=(
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    entry_points={
        'console_scripts': [
            "synapse-uploader = synapse_uploader.cli:main"
        ]
    },
    install_requires=[
        "synapseclient>=1.9.4,<2.0.0"
    ]
)
