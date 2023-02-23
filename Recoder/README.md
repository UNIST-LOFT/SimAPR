# Recoder
A PyTorch Implementation of "A Syntax-Guided Edits Decoder for Neural Program Repair"

## Patch Generation

### 0. Set environment

You need to install java, defects4j, [anaconda](https://www.anaconda.com/). Also, you need a GPU to run Recoder.
If you want to run SimAPR in container, you need `--gpus=all` option when you create a container.

Then, run
```
conda env create -f data/env.yaml
conda activate recoder
```

### 1. Get model

You can train model yourself (see below) or get the pre-trained model from docker image.

```
sudo docker pull zqh111/recoder:interface
```
Model is in `/root/Repair/checkpointSearch/best_model.ckpt`.
Copy this file to this directory.

```
mkdir checkpointSearch
cp /root/Repair/checkpointSearch/best_model.ckpt ./checkpointSearch
```

### 2. Generate patch candidates

In Recoder, project is notated as `{subject}-{version id}`.

    For Chart-1,

    ```
    python3 testDefect4j.py Chart-1
    ```

    If finished, run

    ```
    python3 repair.py Chart-1
    ```

### 3. Output
Output files are in `./d4j/<version>/`.
Each `<version>` directory contains the following:
- `switch-info.json`: Meta-information of patch candidates
- Generated patched files