from dataclasses import dataclass, field


@dataclass(slots=True)
class BuildingType:
    code: str
    country: str
    region: str
    building_size_class: object
    building_size_class_ext: object
    year_class: object
    year_class_ext: object
    first_year: object
    last_year: object
    last_year_ext: object
    areas: list = field(default_factory=list)
