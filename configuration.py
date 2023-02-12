from os import path
import configparser


base_path = path.dirname(__file__)
relative_path = "discord.conf"
config_path = path.join(base_path, relative_path)
config = configparser.ConfigParser()


def read() -> configparser.ConfigParser:
    config.read(config_path)
    return config


def write(data: dict):
    sections = list(data.keys())
    for section in sections:
        if not config.has_section(section):
            config.add_section(section)
        for k, v in data[section].items():
            config.set(section, str(k), str(v))
    with open(config_path, "w") as f:
        config.write(f)
