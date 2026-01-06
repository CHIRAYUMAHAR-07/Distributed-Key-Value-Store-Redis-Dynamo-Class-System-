from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="distributed-kv-store",
    version="1.0.0",
    author="Chirayu Mahar",
    author_email="Chirayumahar@gmail.com",
    description="A Redis/Dynamo-inspired distributed key-value store",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CHIRAYUMAHAR-07/distributed-kv-store",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "Topic :: System :: Distributed Computing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "kvstore=kvstore.cli:main",
            "kvstore-coordinator=kvstore.coordinator:main",
            "kvstore-node=kvstore.storage_node:main",
        ],
    },
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.19.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
        "dashboard": [
            "streamlit>=1.12.0",
            "plotly>=5.10.0",
        ],
    },
)