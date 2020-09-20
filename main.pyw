import ctypes
import enum
import json
import os
import typing
import winreg
from io import BytesIO

import requests
from PIL import Image


IMAGE_PATH = "./apod.png"


class WallpaperStyle(enum.Enum):
    CENTER = "0"
    STRETCH = "2"
    FIT = "6"
    FILL = "10"
    SPAN = "22"


def set_reg(reg_path: str, name: str, value: str):
    winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
    registry_key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE
    )
    winreg.SetValueEx(registry_key, name, 0, winreg.REG_SZ, value)
    winreg.CloseKey(registry_key)
    return True


def get_reg(reg_path: str, name: str) -> str:
    winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
    registry_key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ
    )
    value = winreg.QueryValueEx(registry_key, name)
    winreg.CloseKey(registry_key)
    return value[0]


def get_wallpaper_data(save=False) -> dict:
    wallpaper_data = {}
    wallpaper_data["style"] = get_reg("Control Panel\\Desktop", "WallpaperStyle")
    wallpaper_data["tile"] = get_reg("Control Panel\\Desktop", "TileWallpaper")
    wallpaper_data["image"] = get_reg("Control Panel\\Desktop", "Wallpaper")

    if save:
        with open("wallpaper_data.json", "w") as fp:
            json.dump(wallpaper_data, fp)

    return wallpaper_data


def has_wallpaper_changed() -> bool:
    try:
        with open("wallpaper_data.json") as fp:
            prev_wp_data = json.load(fp)
    except (FileNotFoundError, json.JSONDecodeError):
        return True

    if prev_wp_data == get_wallpaper_data():
        return False

    return True


def change_wallpaper(path: str, style: WallpaperStyle, tile=False):
    ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.abspath(path), 3)

    if tile:
        set_reg("Control Panel\\Desktop", "WallpaperStyle", WallpaperStyle.CENTER.value)
        set_reg("Control Panel\\Desktop", "TileWallpaper", "1")
    else:
        set_reg("Control Panel\\Desktop", "WallpaperStyle", style.value)
        set_reg("Control Panel\\Desktop", "TileWallpaper", "0")

    get_wallpaper_data(save=True)


def get_apod_data(key: str) -> typing.Tuple[dict, dict]:
    url = f"https://api.nasa.gov/planetary/apod?api_key={key}"

    try:
        with open("img_data.json") as fp:
            prev_data = json.load(fp)
        with open("apod.png") as fp:  # Check if image exists
            pass
    except (FileNotFoundError, json.JSONDecodeError):
        prev_data = {}

    response = requests.get(url)
    img_data = response.json()
    img_data["json_url"] = url

    with open("img_data.json", "w") as fp:
        json.dump(img_data, fp)

    return img_data, prev_data


def download_apod(img_data: dict, path: str) -> bool:
    if img_data["media_type"] != "image":
        return False

    try:
        response = requests.get(img_data["hdurl"])
    except KeyError:
        response = requests.get(img_data["url"])

    img = Image.open(BytesIO(response.content))
    img.save(path)

    return True


def main():
    with open("key.json") as fp:
        key = json.load(fp)

    img_data, prev_data = get_apod_data(key)

    if img_data == prev_data:
        if has_wallpaper_changed():
            change_wallpaper(IMAGE_PATH, WallpaperStyle.SPAN)
            return 0

    download_apod(img_data, IMAGE_PATH)
    change_wallpaper(IMAGE_PATH, WallpaperStyle.SPAN)

    return 0


if __name__ == "__main__":
    main()
