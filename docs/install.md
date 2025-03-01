# Install

`keyed` is built atop several non-Python dependencies. Unfortunately, this makes it a bit tedious to install.

!!! note

    Contributions improving the installation procedure or documentation are very welcome!

## Platform-agnostic installation approaches

### Using conda/mamba

The most system agnostic way to currently install `keyed` is using `conda` (or `mamba`).

First, create an `environment.yml` file:

```yml title="environment.yml"
name: keyed
channels:
  - conda-forge
  - nodefaults
dependencies:
  - python<=3.12,>3.10
  - ffmpeg
  - cairo
  - pycairo
  - pip
  - pip:
    - "keyed[previewer]"
```

After, run

```console
conda env create -f environment.yml
```

Finally,

```console
conda activate keyed
```

### Docker

!!! note

    Does not support the QT-based animation preview GUI.

It is possible to render `keyed` scenes from the command line using the `dougmercer/keyed` docker image.

```console
cat your_scene.py | docker run -i --rm dougmerer/keyed:latest > output.mov
```

## Platform-specific installation approaches

### Ubuntu/Debian
```shell
sudo apt-get update && apt-get install -y \
    ## Cairo
    libcairo2 \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    gcc \
    ## ffmpeg
    ffmpeg  # (Optional) - You can use `keyed.renderer.RenderEngine.PYAV` instead.
pip install keyed[previewer]
```

### macOS
```shell
brew install cairo ffmpeg
pip install "keyed[previewer]"
```

### Windows

!!! note

    Untested!

1. Download and install `cairo` from [https://www.cairographics.org/download/](https://www.cairographics.org/download/).
2. Download and install `ffmpeg` from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
3. `pip install keyed[previewer]`
