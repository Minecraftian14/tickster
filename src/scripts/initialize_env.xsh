import base64
import datetime, os, sys
import csv, json, math, re
import collections, itertools, functools

from dotenv import dotenv_values, set_key


args = sys.argv[1:]

if "/?" in args or "-h" in args or "--help" in args:
    print(
        "Usage:\n"
        "  script [options]\n"
        "\n"
        "Description:\n"
        "  Creates/updates .env using values defined in .env.template.\n"
        "  For each variable, uses the existing .env value, template default,\n"
        "  or prompts for a new value.\n"
        "\n"
        "Options:\n"
        "  -q, --quiet\n"
        "      Quiet mode. Automatically use existing values or template defaults\n"
        "      without displaying prompts or messages.\n"
        "\n"
        "  -c, --use-current\n"
        "      Use the existing .env value without asking.\n"
        "\n"
        "  -d, --use-default\n"
        "      Use the template default without asking.\n"
        "\n"
        "  -D, --use-default-over-current\n"
        "      When both -c and -d are used, prefer the template default over\n"
        "      the existing .env value.\n"
        "\n"
        "  -h, --help, /?\n"
        "      Show this help message.\n"
        "\n"
        "Files:\n"
        "  .env.template    Template containing the variables and defaults.\n"
        "  .env             File that is created or updated with the selected values.\n"
        "\n"
        "Value selection:\n"
        "  Existing value > Template default > User input\n"
        "  unless the corresponding options change this order.\n"
        "\n"
        "Env Template File:\n"
        "  All values in .env.template are evaluated as Python code.\n"
        "  The result of each expression is used as the value for that variable.\n"
        "\n"
        "  For example:\n"
        "\n"
        "    ARBITRARY_PYTHON_CODE=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')\n"
        "      Evaluates the current date and time.\n"
        "\n"
        "    EXAMPLE_WITH_MESSAGE=ask_user(message='This is a custom message')\n"
        "      Uses a custom prompt message.\n"
        "\n"
        "    EXAMPLE_WITH_A_NOTE=ask_user(note='This is a custom note.')\n"
        "      Displays a note before prompting for a value.\n"
        "\n"
        "    EXAMPLE_WITH_DEFAULT=ask_user(default='123456')\n"
        "      Uses '123456' as the default value if accepted.\n"
        "\n"
        "    EXAMPLE_WITH_VALUE=('A fixed value')\n"
        "      Sets the variable to a fixed value without prompting.\n"
        "\n"
        "  Python expressions can use the modules and functions available to the script.\n"
        "  The following modules are already imported for use:\n",
        "    " + ", ".join([m for m in globals().keys() if "_" not in m])
    )
    exit()

quiet = "-q" in args or "--quiet" in args
use_current = quiet or "-c" in args or "--use-current" in args
use_default = quiet or "-d" in args or "--use-default" in args
use_default_over_current = (use_current and use_default) and ("-D" in args or "--use-default-over-current" in args)

template = dotenv_values(dotenv_path=".env.template")
env      = dotenv_values(dotenv_path=".env")

for key_name, value_supplier in template.items():
    if not quiet: print("Setting value for:", key_name)

    def ask_user(message="Please enter value", note="", default=""):

        current_available = key_name in env and (key_name != 'LAST_ENV_INIT')
        default_available = default != ""

        if ((not (current_available or default_available)) or not quiet) and note != "":      print(note)

        skip_current = use_default and default_available and use_default_over_current

        if current_available and not skip_current:
            if not quiet: print("Current Value is:", env[key_name])
            if use_current or input("Do you want to change it? [y/n]").lower() != 'y':
                return env[key_name]

        if default != "":
            if not quiet: print("Default Value is:", default)
            if use_default or input("Do you want to change it? [y/n]").lower() != 'y':
                return default

        return input(f"{message}: ")

    value = eval(value_supplier, globals(), locals())
    if not quiet: print("Received value:", value)
    set_key(".env", key_name, str(value))
    if not quiet: print()
