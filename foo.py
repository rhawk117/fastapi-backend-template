from pathlib import Path
from pprint import pprint as pp
import toml



def main() -> None:
    toml_path = Path(".secrets/example.toml")
    toml_dict = toml.load(toml_path)
    pp(toml_dict)
    print('keys: ', list(toml_dict.keys()))

if __name__ == "__main__":
    main()