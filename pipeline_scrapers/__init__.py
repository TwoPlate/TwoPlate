"""
Pipeline scrapers for Kernohan Engineering Sales Pipeline.
"""
from pipeline_scrapers.gets import (
    GETSScraper,
    NelsonCityCouncilScraper,
    TasmanDistrictCouncilScraper,
    MarlboroughDistrictCouncilScraper,
    PortNelsonScraper,
)

ALL_SCRAPERS = [
    GETSScraper,
    NelsonCityCouncilScraper,
    TasmanDistrictCouncilScraper,
    MarlboroughDistrictCouncilScraper,
    PortNelsonScraper,
]

__all__ = [
    "ALL_SCRAPERS",
    "GETSScraper",
    "NelsonCityCouncilScraper",
    "TasmanDistrictCouncilScraper",
    "MarlboroughDistrictCouncilScraper",
    "PortNelsonScraper",
]
