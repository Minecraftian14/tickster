import json
import sys
from pathlib import Path

args = sys.argv[1:][::-1]

if "/?" in args or "-h" in args or "--help" in args:
    print(
        "Usage:\n"
        "  run_project [options]\n"
        "\n"
        "Description:\n"
        "  Runs one of the project's applications or development tools.\n"
        "\n"
        "Options:\n"
        "  -s, --source SOURCE\n"
        "      Select what to run.\n"
        "\n"
        "      Available sources:\n"
        "        frontend, fe\n"
        "        devtools, dt\n"
        "        business, bl\n"
        "\n"
        "  -d, --dry-run\n"
        "      Show the command that would be executed without running it.\n"
        "\n"
        "  -t, --tool-args\n"
        "      Treat all following arguments as arguments for the underlying tool.\n"
        "\n"
        "  -p, --program-args\n"
        "      Treat all following arguments as arguments for the program.\n"
        "      This is the default.\n"
        "\n"
        "  -h, --help, /?\n"
        "      Show this help message.\n"
        "\n"
        "Argument Handling:\n"
        "  Arguments are passed to the selected tool or program.\n"
        "\n"
        "  By default, arguments are passed to the program. Use --tool-args\n"
        "  to switch to passing arguments to the underlying tool.\n"
    )
    exit()

config = Path("run.json")
if not config.exists():
    print("No run config found! (run.json)")
    exit(-1)
config = json.loads(config.read_text())

source = None
stage = True
dry_run = False
background = False
arg_capture_state = "prog"
tool_args = []
prog_args = []

while len(args) > 0:
    command = args.pop()
    if len(command) >= 3 and command[0] == '-' and command[1] != '-':
        for sub_command in command[1:]: args.append("-" + sub_command)
        command = args.pop()
    match command:
        case "-s" | "--source":
            source = args.pop()
        case "-w" | "--weight":
            match args.pop():
                case "a" | "any": weight = "any"
                case "l" | "light": weight = "light"
                case "m" | "mid": weight = "mid"
                case "h" | "heavy": weight = "heavy"
        case "-t" | "--tool-args": arg_capture_state = "tool"
        case "-p" | "--program-args": arg_capture_state = "prog"
        case "-y" | "--yes": stage = False
        case "-d" | "--dry-run": dry_run = True
        case "-b" | "--background": background = True
        case _:
            match arg_capture_state:
                case "tool": tool_args.append(command)
                case "prog": prog_args.append(command)

if source is None:
    print("Please specify the source name to run! Available options:")
    for name, atom in config['atom'].items():
        if "alias" not in atom: print(f"  {name}")
        else: print(f"  {name} or {atom["alias"]}")
    exit()

aliases = {}
for name, atom in config['atom'].items():
    if "alias" in atom:
        aliases[atom["alias"]] = atom
config['atom'] = {**aliases, **config['atom']}

if source not in config['atom']:
    print(f"Unknown source '{source}'. Pick one from:", config['atom'].keys())
    exit()

if stage:
    print("Please confirm:")
    print("  Source      :", source)
    print("  Stage       :", stage)
    print("  Dry Run     :", dry_run)
    print("  Background  :", background)
    print("  Tool Args   :", tool_args)
    print("  Program Args:", prog_args)
    if input("[y/n]").lower() != 'y': exit()

atom = config['atom'][source]
command = None
lta = len(tool_args) == 0
lpa = len(prog_args) == 0
tool_args = [f'"{x}"' for x in tool_args]
prog_args = [f'"{x}"' for x in prog_args]

if lta and lpa and "bare_command" in config: command = atom["bare_command"]
elif lta and "command_prog_args" in config: command = atom["command_prog_args"]
elif lpa and "command_tool_args" in config: command = atom["command_tool_args"]
else: command = atom["command"]

parts = []
for part in command.split():
    if part == "{tool_args}": parts.extend(tool_args)
    elif part == "{prog_args}": parts.extend(prog_args)
    else: parts.append(part)

if dry_run:
    print(parts)
else:
    if background:
        @(parts) &
    else:
        @(parts)

if if: pass