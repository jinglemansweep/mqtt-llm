"""Setup script for mqtt_llm package."""

from setuptools import find_packages, setup

setup(
    name="mqtt-llm",
    version="0.1.0",
    description="MQTT to Ollama bridge for LLM interactions",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.11",
    entry_points={
        "console_scripts": [
            "mqtt-llm=mqtt_llm.main:main",
        ],
    },
)
