"""Sentiment analysis module — LLM and Perplexity integration.

TODO (Phase 3): Implement sentiment signals as strategy inputs.

Planned integrations:
- OpenAI (or another LLM): classify news headlines / earnings calls as
  positive/negative/neutral with a confidence score.
- Perplexity: automated research summaries for a given symbol or sector.

Sentiment scores must be treated as one input among many, not as standalone
signals. Always validate that sentiment adds real predictive value (measured
via out-of-sample testing) before including it in live strategies.
"""
