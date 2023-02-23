# AlphaRepair

## Patch Generation

### 0. Set environment

You need to install java, defects4j, [anaconda](https://www.anaconda.com/).
If you want to run SimAPR in container, you need `--gpus=all` option when you create a container.

Then, run

```
conda env create -f data/env.yaml
conda activate alpha
```

### 1. Generate patch candidates
In alpha-repair, project version is notated as `{subject}-{version id}`.

    For Chart-1,

    ```
    python3 experiment.py --bug_id Chart-1 --output_folder d4j --skip_v --re_rank --beam_width 5 --top_n_locations 40
    ```

### 2. Output
Output files are in `./d4j/<version>/`.
Each `<version>` directory contains the following:
- `switch-info.json`: Meta-information of patch candidates
- Generated patched files