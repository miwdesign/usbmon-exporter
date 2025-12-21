import collections
import pathlib


def build_usb_id_map():
    usb_id_map = collections.defaultdict(dict)
    sysfs_path = pathlib.Path("/sys/bus/usb/devices")

    for device_path in sysfs_path.iterdir():
        if device_path.is_dir():
            busnum_file = device_path / "busnum"
            devnum_file = device_path / "devnum"

            try:
                busnum = int(busnum_file.read_text().rstrip())
                devnum = int(devnum_file.read_text().rstrip())
            except (FileNotFoundError, ValueError):
                continue

            usb_id = device_path.name
            usb_id_map[busnum][devnum] = usb_id

    return usb_id_map
