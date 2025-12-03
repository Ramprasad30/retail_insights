# Retail Insights Assistant

AI-powered retail analytics platform with multi-agent architecture for automated insights and conversational Q&A.

## Features

- **Multi-Agent System**: 4 specialized AI agents (Query Resolution, Data Extraction, Validation, Synthesis)
- **Summary Mode**: Automated performance dashboards with visualizations
- **Q&A Mode**: Conversational analytics in natural language
- **Fast Processing**: DuckDB for analytical queries on 180K+ records
- **Interactive UI**: Streamlit web interface with real-time insights

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API key
cp env.template .env
# Edit .env and add: OPENAI_API_KEY=your_key_here

# 3. Run application
python main.py
```

Get your OpenAI API key: https://platform.openai.com/api-keys

## Project Structure

```
├── backend/              # Core logic (agents, data processing, config)
├── frontend/             # Streamlit web interface
├── tests/                # Test suite
├── scripts/              # Utility scripts (setup, examples)
├── data/                 # Data storage (CSV files)
├── docs/                 # Documentation
├── main.py              # Application entry point
├── env.template         # Environment template
└── requirements.txt     # Python dependencies
```

## Usage

### Run Application
```bash
python main.py
```

### Run Tests
```bash
python tests/test_system.py
```

### Setup Verification
```bash
python scripts/setup.py
```

### View Examples
```bash
python scripts/example_usage.py
```

## Technology Stack

- **Backend**: Python, LangChain, LangGraph, DuckDB
- **Frontend**: Streamlit, Plotly
- **AI/LLM**: OpenAI GPT-4
- **Data**: Pandas, DuckDB (180K+ records)

## Requirements

- Python 3.10+
- OpenAI API key
- 4GB+ RAM

## Architecture

Multi-agent system with 4 specialized agents:

1. **Query Resolution Agent** - Converts natural language to SQL
2. **Data Extraction Agent** - Executes queries and retrieves data
3. **Validation Agent** - Ensures data quality
4. **Synthesis Agent** - Generates insights and responses

See `docs/ARCHITECTURE.md` for detailed architecture documentation.

## Documentation

- **Architecture**: `docs/ARCHITECTURE.md`
- **API Documentation**: `docs/README.md`
- **Setup Guide**: `docs/SETUP_INSTRUCTIONS.md`
- **Presentation**: `docs/PRESENTATION.md`

## Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
python tests/test_system.py
```

### Project Modules

- `backend/agents.py` - Multi-agent system implementation
- `backend/data_processor.py` - Data processing layer
- `backend/config.py` - Configuration management
- `frontend/app.py` - Streamlit UI

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests
5. Submit pull request

## License

This project is provided as-is for evaluation purposes.

---

**For detailed documentation, see the `docs/` directory.**
