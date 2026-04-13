"""Latn to Keyboard Input Converter

This script converts latn to keyboard input format
(e.g., lí -> li2) and supports multiple latn systems.

Note: The core logic has been extracted into the `scripts.latn` package.
This file serves as a command-line interface.
"""

from scripts.latn import (
    create_converter,
    list_systems,
)

if __name__ == "__main__":
    import sys

    def print_usage():
        print("Usage: python latn_converter.py <romanized_text> [system]")
        print("Example: python latn_converter.py 'lí' PUJ")
        print(f"Available systems: {', '.join(list_systems())}")

    if len(sys.argv) > 1:
        romanized_text = sys.argv[1]
        system = sys.argv[2] if len(sys.argv) > 2 else "PUJ"

        try:
            converter = create_converter(system)
            result = converter.to_keyboard(romanized_text)
            print(result)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            print_usage()
            sys.exit(1)
    else:
        print_usage()