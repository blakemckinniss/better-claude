# Firecrawl Integration Setup

The hooks system now includes Firecrawl web search and scraping capabilities for enhanced context.

## Configuration

1. **API Key**: Set your Firecrawl API key in the environment:
   ```bash
   export FIRECRAWL_API_KEY="fc-your-api-key-here"
   ```
   
   Or add it to your `.env` file:
   ```
   FIRECRAWL_API_KEY=fc-your-api-key-here
   ```

2. **Usage**: The Firecrawl injection automatically triggers when:
   - User prompts contain web search indicators (latest, current, best practices, documentation, etc.)
   - User prompts contain URLs to scrape
   - Prompts mention technology queries that would benefit from current web information

## Features

### Automatic Web Search
- Detects when prompts would benefit from current web information
- Generates optimized search queries based on prompt content
- Returns up to 3 relevant search results with markdown content
- Technology-specific search enhancement (Python, JavaScript, React, etc.)

### URL Scraping
- Automatically scrapes any URLs mentioned in user prompts
- Extracts clean markdown content from web pages
- Supports PDF parsing and main content extraction
- Limits content size to prevent token explosion

### AI Integration
- Firecrawl data is processed by the AI context optimizer
- Web search results are integrated into role-based prompts
- Provides current information to enhance AI responses

## Example Triggers

These prompt patterns will trigger Firecrawl web search:
- "What are the latest React best practices?"
- "Show me current documentation for Docker deployment"
- "What's new in Python 3.12?"
- "Best practices for AWS security in 2024"

URLs in prompts are automatically scraped:
- "Analyze this documentation: https://docs.example.com/api"
- "What does https://github.com/user/repo say about installation?"

## Performance

- Runs asynchronously in parallel with other injection modules
- 15-second timeout for search requests, 20-second for scraping
- Graceful fallback when API is unavailable
- Does not break hook execution on errors

## Testing

Run Firecrawl-specific tests:
```bash
pytest hook_test.py -k "firecrawl" -v
```

All integration tests pass with the new async parallel execution system.