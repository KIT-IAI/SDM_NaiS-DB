# NaiS Database


* [TABULA](https://episcope.eu/) - Typology Approach for Building Stock Energy Assessment
* [IWU-NWG](https://www.datanwg.de/) - Research Database Nonresidential Buildings
* [Albauatlas](https://www.altbauatlas.de/) - Historic building materials and constructions
* [EPD](https://ibu-epd.com/veroeffentlichte-epds/) - Environmental Product Declaration
* [CRREM Pathways](https://crrem.org/) - Carbon Risk Real Estate Monitor


## Requirements

- Python 3.12
- `uv`
- the raw source files in the expected `data/raw/` folders


## How to use

```bash
uv python install 3.12
uv sync
uv run python -m scripts.build_all
```


## How to cite

```bibtex
@software{SDM_NaiS-DB,
	title        = {{SDM\_NaiS-DB}},
	author       = {Yingcong Zhong, Andreas Geiger},
	url          = {https://github.com/KIT-IAI/SDM_NaiS-DB},
	year         = {2025}
}
```











