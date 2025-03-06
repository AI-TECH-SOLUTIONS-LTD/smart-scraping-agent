# SmartScrapingAgent

**SmartScrapingAgent** is a Python package designed to simplify web scraping using state-of-the-art LLMs (Large Language Models) and customizable schemas. With this package, you can extract structured data efficiently from large, complex web pages.

---

## Installation

### Step 1: Install Playwright
Install Playwright, which is required for handling headless browsing:
```bash
playwright install
```

### Step 2: Install SmartScrapingAgent
Install the Smart Scraping Agent package:
```bash
pip install ai-tech-crawler
```

---

## Usage
Here is a step-by-step guide to using the **Smart Scraping Agent** package:

**N.B.: This import is required only for jupyter notebooks, since they have their own eventloop**
```bash
pip install nest-asyncio
```

```python
import nest_asyncio

nest_asyncio.apply()
```


### Step 1: Import Required Modules
Import necessary modules and classes:
```python
import os, json
from dotenv import load_dotenv


load_dotenv()
```


### Step 2: Define the Configuration
Set up the configuration for the scraping pipeline:
```python
agent_config = {
    "llm": {
        "api_key": os.getenv('OPENAI_API_KEY'),
        "model": "openai/gpt-4o-mini",
        # Uncomment for other models
        # "model": "ollama/nemotron-mini",
        # "device": "cuda",
        # "model_kwargs": {'response_format': {"type": "json_object"}}
    },
    "verbose": True,
    "headless": True,
    "max_retries": 3
}
```

### Step 3: Write Your Prompt
Define a simple prompt to guide the scraping process:
```python
simple_prompt = """
Extract all the trending topics, their search volumes, when it started trending and the trend breakdown from the website's content.
"""
```

### Step 4: Load the Schema
Use the schema to define the structure of the extracted data:
Schema can be:
1. `format instruction string with examples`
2. `dict`
3. `json`
4. `pydantic` or `BaseModel`

```python
schema_ = {
    'trends': [
        {
            'topic': 'Trending topic',
            'search_volume': 'Search Volume of a topic',
            'started': 'Time when it started trending',
            'trend_breakdown': 'A trend may consist of multiple queries that are variants of the same search or considered to be related. Trend breakdown details these queries.'
         }
    ],
    'other_links':[
        'list of any other reference URLs'
    ]
}
```

**N.B.**: For better results use a valid `pydantic` schema which is a subclass of `BaseModel`.

### Step 5: Instantiate the SmartScraperAgent
Create an instance of the **SmartScraperAgent** with the necessary parameters:
```python
from ai_tech_crawler import SmartScraperAgent

url = "https://trends.google.com/trending"

smart_scraper_agent = SmartScraperAgent(
    prompt=simple_prompt,
    source=url,
    config=agent_config,
    schema=schema_
)
```

### Step 6: Run the Scraper
Execute the scraping pipeline and process the results:
```python
result = smart_scraper_agent.run()
print(json.dumps(result, indent=4))
```

### Load a Webpage content as Markdown
```python
markdown_content = smart_scraper_agent.get_markdown()
print(markdown_content)
```

### Load recursive webpages and split it into Documents
```python
documents = smart_scraper_agent.load_indepth_and_split(depth=2)
print(documents[0].page_content)
print(documents[0].nmetadata)
```

---

## Key Features
- **LLM-Powered**: Leverage advanced models like GPT for smart data extraction.
- **Schema-Driven**: Flexible schema design to control output format.
- **Headless Browsing**: Playwright integration for efficient, non-visual browsing.
- **Customizable**: Fine-tune the pipeline using configurations and custom merge methods.

---

## Contributing
Contributions are welcome! Feel free to submit issues or pull requests on the [GitHub repository](https://github.com/AI-TECH-SOLUTIONS-LTD/smart-scraping-agent).

---

## License
This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
