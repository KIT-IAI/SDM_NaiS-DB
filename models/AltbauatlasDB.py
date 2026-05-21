from dataclasses import dataclass


@dataclass(slots=True)
class AltBauConstruction:
    file_name: str
    name: str
    element_type: str
    material: list
    postal_code: str
    first_year: object
    last_year: object
    u_value: str
