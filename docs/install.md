---
hide:
  - navigation
---

# Installing `keyed`

This page covers the basic installation process for the core `keyed` package.

!!! info "keyed-extras Users"

    If you're a sponsor <!-- md:sponsors --> with access to `keyed-extras`, please follow the `keyed-extras` [installation documentation](https://extras.keyed.dev/install/) instead, which includes all necessary instructions for both packages.

!!! note

    Contributions improving the installation procedure or documentation are welcome!

`keyed` requires some non-Python dependencies for its rendering capabilities. 

| Dependency | Required for | Installation Priority |
|------------|--------------|----------------------|
| [Cairo](https://www.cairographics.org/) | Core rendering functionality | Required |
| [FFmpeg](https://ffmpeg.org/) | Faster video rendering | Recommended |


## Installation Methods

Choose the method that works best for your system:

??? tip "(Recommended) conda - Any Platform"

    Create an `environment.yml` file:

    ```yaml title="environment.yml"
    name: keyed
    channels:
    - conda-forge
    - nodefaults
    dependencies:
    - python<3.13,>=3.11
    - ffmpeg
    - cairo
    - pip
    - pip:
        - "keyed[previewer]"
    ```

    After creating your environment.yml file, run:


    ```console
    conda env create -f environment.yml
    conda activate keyed
    ```

??? info "Docker"

    The `keyed:latest` Docker image makes it possible to render `keyed` scenes from the command line. Run,

    ```console
    cat your_scene.py | docker run -i --rm ghcr.io/dougmercer/keyed:latest > output.mov
    ```

    !!! note "Limited Capabilities"

        Does not support the animation previewer window.

??? info "Ubuntu/Debian"
    ```shell
    sudo apt-get update && apt-get install -y \
        libcairo2-dev \
        pkg-config \
        python3-dev \
        gcc \
        ffmpeg  # Optional - enables faster rendering
    pip install keyed[previewer]
    ```

??? info "macOS"
    ```shell
    brew install cairo pkg-config ffmpeg
    pip install "keyed[previewer]"
    ```

??? info "Fedora"
    ```shell
    sudo dnf install cairo-devel pkg-config python3-devel ffmpeg
    pip install keyed[previewer]
    ```

??? info "Arch"
    ```shell
    sudo pacman -S cairo pkgconf ffmpeg
    pip install keyed[previewer]
    ```

??? info "openSUSE"
    ```shell
    sudo zypper install cairo-devel pkg-config python3-devel ffmpeg
    pip install keyed[previewer]
    ```

??? warning "Windows"

    (Untested!)

    1. Download and install `cairo` from [https://www.cairographics.org/download/](https://www.cairographics.org/download/).
    2. Download and install `ffmpeg` from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
    3. `pip install keyed[previewer]`


## FAQ

> What happens if I don't install ffmpeg?

`keyed` will use `pyav` as its rendering engine. In practice I found this to about twice as slow as `ffmpeg`.

> I ran into some other problem...

Please create an [issue](https://github.com/dougmercer/keyed/issues) on the `keyed` GitHub!
