# Azure AI Foundry Multi-Agent Demo

This project showcases a simple multi-agent workflow built on top of Azure AI Foundry's multi-agent framework. The demo focuses on researching stock prices by orchestrating specialized agents that collaborate to retrieve market information via the Serper.dev search API.

## Features
- Multi-stage orchestrator that routes between price, news, and analysis specialists for both first-pass and follow-up requests.
- Modular prompt builders and stage metadata so agent instructions stay organized and easy to extend.
- Research toolkit that blends Polygon.io quotes, historical metrics, and Serper.dev headlines into a unified payload.
- Streamlit UI with interactive Altair charts, chat-based follow-ups, and quick ticker presets.
- Environment variables managed through a `.env` file for API keys and Azure credentials.
- Poetry-driven workflow with pytest/pytest-cov for automated testing and coverage enforcement.

## Quick Start
1. Install dependencies: `poetry install`
2. Copy `.env.example` to `.env` and populate the required values.
3. Run the CLI demo: `poetry run python -m azure_ai_foundry_demo.cli --ticker MSFT`
4. Launch the Streamlit UI: `poetry run streamlit run src/azure_ai_foundry_demo/streamlit_app.py`
5. Execute tests with coverage: `poetry run pytest --cov`

## Testing & Coverage
- Run the fast suite with `poetry run pytest` during development.
- Generate a detailed report with `poetry run pytest --cov --cov-report=term-missing`; the project is configured to fail if coverage drops below 80%.
- Coverage focuses on the library modules under `azure_ai_foundry_demo/` and intentionally omits the Streamlit UI and Azure integration layers that require live services.

## Project Structure
```
.
├── pyproject.toml
├── README.md
├── .env.example
├── src/
│   └── azure_ai_foundry_demo/
│       ├── __init__.py
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── orchestrator.py
│       │   ├── runner.py
│       │   ├── tooling.py
│       │   ├── prompt_builders.py
│       │   ├── stage_models.py
│       │   ├── stage_specs.py
│       │   └── utils.py
│       ├── clients/
│       │   ├── __init__.py
│       │   ├── polygon.py
│       │   └── serper.py
│       ├── config.py
│       ├── models.py
│       ├── streamlit_app.py
│       └── workflow.py
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_polygon_client.py
    ├── test_serper_client.py
    ├── test_tooling.py
    ├── test_utils.py
    ├── test_prompt_builders.py
    └── test_workflow.py
```

## Notes
- This project targets Python 3.11.
- The Serper.dev and Polygon.io API keys plus Azure AI credentials must be supplied via environment variables; see `.env.example`.
- The Azure AI Foundry multi-agent features used here may require preview access; consult the Azure documentation for details on enabling the agents feature in your workspace.
