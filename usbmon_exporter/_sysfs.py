import pathlib


def build_usb_id_map():
    usb_id_map = {}
    sysfs_path = pathlib.Path("/sys/bus/usb/devices")

    for device_path in sysfs_path.iterdir():
        if device_path.is_dir():
            busnum_file = device_path / "busnum"
            devnum_file = device_path / "devnum"

            try:
                busnum = int(busnum_file.read_text().rstrip())
                devnum = int(devnum_file.read_text().rstrip())
                usb_id = device_path.name

                key = (busnum, devnum)
                usb_id_map[key] = usb_id
            except (FileNotFoundError, ValueError):
                continue

    return usb_id_map
