# Patches

* RidgeRun's IMX477 (Raspberry Pi HQ Camera) patches for the Nvidia Linux 4.9 kernel tag 32.4.3 (nano and nx). These patches, like the Linux kernel itself are licensed under the GNU General Public License.

## Example

To build a nano image with IMX477 support:

```
tib nano --patches extras/patches/nano_4.4.3_l4t32.4.3_rbpv3_imx477_support.patch --menuconfig
```

Will prepare for the build and apply the patch. Eventually you'll be presented
with a blue menu and a bunch of choices. Navigate to IMX477 support as shown
below, press `y` to enable the option, press `esc` until you're promted to save,
select `Yes` and press `enter`.

```
Device Drivers  --->
  <*> Multimedia support  --->
      NVIDIA overlay Encoders, decoders, sensors and other helper chips  --->
          <*> IMX477 camera sensor support
```

Please report any issues with the driver (not the build process) [here](https://github.com/RidgeRun/NVIDIA-Jetson-IMX477-RPIV3/issues).