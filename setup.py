from setuptools import setup, find_packages

setup(
    name="loom",
    version="0.1.0",
    description="Tailor resumes using the OpenAI Responses API",
    packages=find_packages(),
    install_requires=[
        "typer",
        "python-docx",
        "openai",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "loom=src.cli:app",
        ],
    },
    python_requires=">=3.12",
)