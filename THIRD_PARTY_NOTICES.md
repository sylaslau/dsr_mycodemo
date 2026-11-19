**Third-party notices**  
Mycelly (repository `dsr_mycodemo`) contains no third-party code. Python dependencies are installed from PyPI under their own licences (see `pyproject.toml`) and are not bundled here. This file records the sources of the data, reference values and ideas used in the project.  
**Published datasets (**`data/interim/extracted/`**)**  
Values were extracted from the publications below and harmonised into one shared schema; full citations are given in `dataset.csv`. Licences are listed as stated by each source. Material-side values also underlie `data/processed/materials/property_table.csv` (d004, d005, d006, d007, d016, d017, d023) and `post_treatment.csv` (d003, d004, d005, d006, d007, d016, d017, d023).  
  
|  |  |  |  |  
| - | - | - | - |  
| **ID** |  **Source** |  **Side** |  **Licence** |  
| d001 |  Dzulkefli 2018, doi 10.1016/j.dib.2018.09.008 |  food |  not stated |  
| d002 |  Musci 2025, doi 10.2478/gsr-2024-0014 |  food |  not stated |  
| d003 |  Gomaa et al. 2024, [https://github.com/m-AI-celium/Myceilum_Growth_Dataset](https://github.com/m-AI-celium/Myceilum_Growth_Dataset "https://github.com/m-AI-celium/Myceilum_Growth_Dataset") |  materials |  CC BY-NC-SA 4.0 (repository) |  
| d004 |  Bhaskar 2026, [https://data.mendeley.com/datasets/zd9ncf85k3/1](https://data.mendeley.com/datasets/zd9ncf85k3/1 "https://data.mendeley.com/datasets/zd9ncf85k3/1") |  materials |  not stated |  
| d005 |  Elsacker 2019, [https://data.mendeley.com/datasets/r8m4y7rv8j/1](https://data.mendeley.com/datasets/r8m4y7rv8j/1 "https://data.mendeley.com/datasets/r8m4y7rv8j/1") |  materials |  not stated |  
| d006 |  Hysek 2025, [https://zenodo.org/records/17104804](https://zenodo.org/records/17104804 "https://zenodo.org/records/17104804") |  materials |  not stated |  
| d007 |  Irbe 2026, doi 10.1016/j.nxmate.2026.102309 |  materials |  CC BY |  
| d009 |  Elsacker 2022, doi 10.3390/biomimetics7020057 |  materials |  not stated |  
| d012 |  Pacheco-Sanchez 2026, doi 10.3390/molecules31193533 |  food |  CC BY 4.0 |  
| d016 |  Vasatko 2022, doi 10.3390/biomimetics7020051 |  materials |  CC BY |  
| d017 |  Jimenez-Obando 2025, doi 10.3390/jof11060460 |  materials |  CC BY |  
| d020 |  Dao 2023, doi 10.3389/fmicb.2023.1130196 |  materials |  not stated |  
| d021 |  Zervakis 2001, doi 10.1007/BF02818539 |  food |  not stated |  
| d023 |  Houette 2022, doi 10.3390/biomimetics7030103 |  materials |  CC BY |  
| d024 |  Patil 2025, doi 10.5281/zenodo.18066556 |  food |  CC BY-SA |  
| d025 |  Gebru 2024, doi 10.1080/12298093.2024.2399353 |  food |  CC BY-NC 4.0 |  
| d026 |  Akcay 2023, doi 10.1038/s41598-023-40200-x |  food |  CC BY 4.0 |  
| d027 |  Salifu 2024, doi 10.1016/j.bgtech.2024.100137 |  food |  CC BY-NC-ND 4.0 |  
  
   
**Consensus cultivation table**  
`data/processed/food/cultivation_baseline.csv` and `cultivation_guide_text.csv` form our own table of typical cultivation values, compiled with NotebookLM and checked row by row rather than page by page. The `source_reference` column names the books and guides behind each row: Stamets (2000, Ten Speed Press); Chang & Miles (2004, CRC Press); MushWorld (2004); Royse (2001, 2003, Penn State Extension); ICAR-DMR Solan (2020); Agromisa Agrodok-40 (2003); Philippoussis et al. (2001); UN CSAM (2020); a consensus of commercial spawn suppliers.  
**Own estimates and data**  
- `data/interim/extracted/cn_ingredients.csv`: carbon and nitrogen contents are our own typical values per ingredient or ingredient category, not measurements from a single source.  
- `data/interim/coverage_syldd.csv` and the syldd records: our own test batch of *Pleurotus ostreatus* (October 2026).  
