from typing import List


def choices_to_enum(choices: List[tuple]):
    """
    Convert Django choices to GraphQL enum format.
    Adds 'A_' prefix to numeric values to make them valid GraphQL enum names.
    """
    return {
        item[0]: (
            f"A_{item[0]}" if item[0].replace('.', '', 1).replace('-', '', 1).isdigit() or item[0].startswith('-')
            else item[0]
        )
        for item in choices
    }