# thdv - [telegram-history-dump](https://github.com/tvdstaaij/telegram-history-dump) viewer

## Installation

1. Install [uv](https://docs.astral.sh/uv/);
2. Run `uv run thdv`.

## Tips

The program tries these locations for the telegram-history-dump manifest file on start-up:

- `~/telegram-history-dump/output/progress.json`
- `(working directory)/output/progress.json`
- `(program directory)/output/progress.json`
- `(program symlink directory)/output/progress.json`

If the program cannot find the file at these locations, it prompts your to choose one manually. You could run `thdv` from the telegram-history-dump directory, or copy / symlink the `output` directory of telegram-history-dump to the program directory. Either method prevents the program from asking you for file location.
