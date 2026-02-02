from app.logging_config import setup_logging
from app.runner import AgentRunner


def main() -> None:
    setup_logging()
    runner = AgentRunner()
    runner.run()


if __name__ == "__main__":
    main()
