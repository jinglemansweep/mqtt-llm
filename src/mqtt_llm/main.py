"""Main entry point for MQTT-LLM bridge application."""


def main():
    """Run the main entry point."""
    from .cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
