from dataclasses import dataclass


@dataclass(slots=True)
class YearClass:
    code: str
    country: str
    first_year: object
    last_year: object
