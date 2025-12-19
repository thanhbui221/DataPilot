# Ollama Setup Guide

This guide will help you set up Ollama for DataPilot.

## What is Ollama?

Ollama is a tool that makes it easy to run large language models locally. It handles model downloads, management, and provides a simple API.

## Installation

### macOS

```bash
# Install using Homebrew
brew install ollama

# Or download from https://ollama.ai/download
```

### Linux

```bash
# Install using curl
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows

Download the installer from https://ollama.ai/download

## Start Ollama

After installation, start the Ollama service:

```bash
ollama serve
```

This will start the Ollama API server on `http://localhost:11434` (default port).

## Download Models

DataPilot works with various open-source models. Recommended models:

### For Intent Clarification & Insights (General Purpose)

```bash
# Mistral 7B (Recommended - good balance)
ollama pull mistral

# LLaMA 3 8B (Alternative)
ollama pull llama3

# Qwen 2.5 7B (Good alternative)
ollama pull qwen2.5:7b
```

### For SQL Generation (Code-Focused)

```bash
# CodeLlama 7B (Best for SQL)
ollama pull codellama:7b

# DeepSeek Coder (Alternative)
ollama pull deepseek-coder:6.7b
```

### Unified Model (Recommended for POC)

For Phase 1, use a single model for all agents:

```bash
# Mistral is a good general-purpose model
ollama pull mistral
```

Then update `src/config/config.yaml`:
```yaml
llm:
  model_name: "mistral"  # Use the same model for all agents
```

## Verify Installation

Test that Ollama is working:

```bash
# Test with a simple query
ollama run mistral "Hello, how are you?"
```

Or test the API:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

## Configuration

Update `src/config/config.yaml`:

```yaml
llm:
  provider: "ollama"
  base_url: "http://localhost:11434"  # Default Ollama URL
  model_name: "mistral"  # Change to your preferred model
  temperature: 0.7
  max_tokens: 2048
  use_unified_model: true
  timeout: 60
```

## Model Recommendations

| Use Case | Recommended Model | Command |
|----------|------------------|---------|
| General purpose (POC) | Mistral 7B | `ollama pull mistral` |
| SQL generation | CodeLlama 7B | `ollama pull codellama:7b` |
| Best quality | LLaMA 3 8B | `ollama pull llama3` |
| Smaller/faster | Qwen 2.5 3B | `ollama pull qwen2.5:3b` |

## Troubleshooting

### Ollama not starting

```bash
# Check if Ollama is running
ps aux | grep ollama

# Restart Ollama
ollama serve
```

### Model not found

```bash
# List available models
ollama list

# Pull the model again
ollama pull <model-name>
```

### Connection refused

- Make sure Ollama is running: `ollama serve`
- Check the port: Default is 11434
- Verify URL in config: `base_url: "http://localhost:11434"`

### Out of memory

- Use smaller models (3B or 7B instead of 13B+)
- Close other applications
- Consider using quantized models (they're automatically quantized by Ollama)

## Next Steps

1. ✅ Install Ollama
2. ✅ Start Ollama service
3. ✅ Pull a model (e.g., `ollama pull mistral`)
4. ✅ Update `config.yaml` with model name
5. ✅ Run DataPilot: `python main.py`

## Resources

- [Ollama Documentation](https://github.com/ollama/ollama)
- [Available Models](https://ollama.ai/library)
- [Ollama API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md)

