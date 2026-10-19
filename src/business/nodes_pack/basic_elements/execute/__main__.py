import pyperclip


# noinspection type-hints, unresolved-references
def execute(output: str) -> [{'name': 'output', 'type': str, 'viz': 'side'}]:
    output = str(output)
    pyperclip.copy(output)
    if len(output) > 100000: output = output[:99989] + '<TRUNCATED>'
    return {'hint': 'text', 'data': output}


main_callable = execute
