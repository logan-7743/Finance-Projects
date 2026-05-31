"""Tests for Perplexity research request/response objects."""

from quant.research import PerplexityResearchRequest, PerplexityResearchResult
from quant.research.perplexity_researcher import PerplexitySearchResult


def test_perplexity_research_request_defaults_are_conservative() -> None:
    request = PerplexityResearchRequest(question="What changed in crypto liquidity this week?")

    assert request.search_mode == "web"
    assert request.temperature == 0.2
    assert "uncertainty" in request.system_prompt.lower()


def test_perplexity_research_result_holds_citations() -> None:
    result = PerplexityResearchResult(
        model="sonar-pro",
        answer_markdown="Summary",
        citations=[
            PerplexitySearchResult(
                title="Source",
                url="https://example.com",
            )
        ],
    )

    assert result.provider == "perplexity"
    assert result.citations[0].url == "https://example.com"
