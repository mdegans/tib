# Camera Profiles

* imx477 provided by RidgeRun and Leopard Imaging

## Installation Instructions

Adapted from [here](https://developer.ridgerun.com/wiki/index.php?title=JetsonTX2/HowTo%27s/NVIDIA_Jetson_ISP_Control#Custom_ISP_Configuration)

(on the Tegra device)

```
sudo rm /var/nvidia/nvcam/settings/nvcam_cache_*
sudo rm /var/nvidia/nvcam/settings/serial_no_*
cp <path>/camera_overrides.isp /var/nvidia/nvcam/settings
sudo chmod 664 /var/nvidia/nvcam/settings/camera_overrides.isp
sudo chown root:root /var/nvidia/nvcam/settings/camera_overrides.isp
```