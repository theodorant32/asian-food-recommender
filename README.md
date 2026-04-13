# Asian Food Intelligence Explorer

Built this to explore ML recommendations while feeding my love for Asian cuisine. Helps you discover dishes based on taste preferences, not just keywords.

## Quick Start

```bash
pip install -r requirements.txt
python run_server.py --reload
# New terminal:
python run_frontend.py
```

## What It Does

- **Recommends dishes** based on your taste (spice level, flavors, textures)
- **Visual taste map** - see where dishes fall on spicy↔mild, light↔rich
- **Find similar dishes** - like mapo tofu but less spicy?
- **Hybrid search** - BM25 + embeddings for better results

## Data

50+ dishes I curated across Chinese, Japanese, Korean, Thai, Vietnamese, Malaysian. Each has taste profile, flavor tags, texture tags.

## Running Tests

```bash
pytest tests/ -v
```

## Docker

```bash
docker-compose up
```

API at localhost:8000, frontend at localhost:8501.
