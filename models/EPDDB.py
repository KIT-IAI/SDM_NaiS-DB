from dataclasses import dataclass


@dataclass(slots=True)
class EpdMaterial:
    file_name: str
    declaration_number: str
    product_unit: str
    owner: str
    version: str
    year_of_exhibition: object
    valid_until: object
    density: str
    raw_density: str
    thermal_conductivity: str
    technical_data: str
