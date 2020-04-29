# thdv - [telegram-history-dump](https://github.com/tvdstaaij/telegram-history-dump) viewer

## Installation

1. Install [Python](https://www.python.org/) and [PyQt5](https://pypi.org/project/PyQt5/);
2. Run `thdv.py`.

## Tips

The program tries these locations for the telegram-history-dump manifest file on start-up:

- `~/telegram-history-dump/output/progress.json`
- `(working directory)/output/progress.json`
- `(program directory)/output/progress.json`
- `(program symlink directory)/output/progress.json`

If the program cannot find the file at these locations, it prompts your to choose one manually. You could copy / symlink the `output` directory of telegram-history-dump to the program directory; or you could copy / symlink `thdv.py` to the telegram-history-dump directory. Either method prevents the program from asking you for file location.
