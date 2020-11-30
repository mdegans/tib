import os

import setuptools

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(THIS_DIR, "README.md")) as readme:
    long_description = readme.read()

setuptools.setup(
    name="tib",
    version="0.1.2",
    description="Create NVIDIA Tegra SD card images on any platform.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    python_requires=">=3.6",
    install_requires=None,
    packages=["tib"],
    package_data={
        "tib": [
            "download_bsp.sh",
            "download_public_sources.sh",
            "download_rootfs.sh",
            "echo.sh",
            "install_deps.sh",
        ]
    },
    entry_points={
        "console_scripts": [
            "tib=tib.__main__:cli_main",
        ]
    },
    author="Michael de Gans",
    author_email="michael.john.degans@gmail.com",
    project_urls={
        "Bug Reports": "https://github.com/mdegans/tib/issues",
        "Source": "https://github.com/mdegans/tib/",
    },
)