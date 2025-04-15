# llm-server

This is an implementation of an LLM server that is designed to handle high throughputs.

## Setup

Run the FastAPI server, from the root execute:

```
uvicorn src.main:app --reload
```

Remeber to authorize by sending the same key of the .ENV in the header or `/docs` UI. 