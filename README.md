# Tegra Image Builder

Scripts to make JetPack SD Card images on any platform.

## Requirements:

* Python 3 (and pip)
* [Multipass](https://multipass.run/)

## Installation:

**NOTE: virtualenv required in Linux because of #6**

```
pip install git+https://github.com/mdegans/tib.git
```

Specific versions can be installed [by using a specific hash, tag name, or git ref](https://pip.pypa.io/en/stable/reference/pip_install/#git).

## Usage:

```
 $ tib --help
usage: __main__.py [-h] [-v {0,1,2}] [-l LOG_FILE] [--no-cleanup] [-m MEM] [-r {a01,a02,b00}] [-o OUT] [--scripts SCRIPTS [SCRIPTS ...]] [--enter-chroot] [--chroot-scripts CHROOT_SCRIPTS [CHROOT_SCRIPTS ...]]
                   [--patches PATCHES [PATCHES ...]] [--menuconfig] [--save-kconfig SAVE_KCONFIG] [--load-kconfig LOAD_KCONFIG]
                   {nano,nx}

Create a custom, flashable, Tegra SD Card image

positional arguments:
  {nano,nx}             board to build an image for

optional arguments:
  -h, --help            show this help message and exit
  -v {0,1,2}, --verbose {0,1,2}
                        logging level (default: 0)
  -l LOG_FILE, --log-file LOG_FILE
                        where to store log file (default: /home/mdegans/Projects/tib/tib.log)
  --no-cleanup          do not delete VM when done (default: False)
  -m MEM, --mem MEM     memory use cap for VM (default: 8G)
  -r {a01,a02,b00}, --revision {a01,a02,b00}
                        jetson nano revision (default: b00)
  -o OUT, --out OUT     sdcard image filename (default: sdcard.img)
  --scripts SCRIPTS [SCRIPTS ...]
                        script(s) to copy and run inside the VM (default: ())
  --enter-chroot        enter a chroot to edit the rootfs interactively (default: False)
  --chroot-scripts CHROOT_SCRIPTS [CHROOT_SCRIPTS ...]
                        script(s) to run inside the rootfs (as aarch64) (default: None)
  --patches PATCHES [PATCHES ...]
                        one or more **kernel** patches to apply at kernel_src.tbz2 root (default: ())
  --menuconfig          customize kernel config interactively using a menu (WARNING: here be dragons! While it's unlikely, you could possibly damage your Tegra or connected devices if the kernel is mis-configured). (default: False)
  --save-kconfig SAVE_KCONFIG
                        filename to save kernel config to (save your menuconfig choices) (default: None)
  --load-kconfig LOAD_KCONFIG
                        filename to load kernel config from (load menuconfig choices) (default: None)

Examples:

Building a more or less stock SD card image:
  tib nano (or) tib nx

Building with some custom kernel patches and enable them in an interactive menu:
  tib nano --patches camera.patch pwm.patch --menuconfig

Customize the kernel using menuconfig:
  tib nano --menuconfig
```
