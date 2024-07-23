'''
    This needs to handle taking links to colorhunt.co and extracting out the actual color palette

    That's very simple to do, so I should consider whether this needs to be a separate file or not
'''

def extract_colorhunt_palette(url: str) -> list[str]:
    '''
    Extract the colors from a colorhunt.co palette link.

    This function takes a link to a colorhunt.co palette and returns a list of the colors.
    The link should be in the form of:
        https://colorhunt.co/palette/7d0a0abf3131ead196f3edc8
        https://colorhunt.co/palette/vvvvvvxxxxxxyyyyyyzzzzzz
    where the link contains the individual colors in the palette directly encoded in it.

    Args:
        url (str): The URL of the colorhunt.co palette.

    Returns:
        list[str]: A list of four color codes, each represented as a string of 6 characters.

    Raises:
        ValueError: If the URL doesn't match the expected format.
    '''

    # Extract the last 24 characters from the URL
    color_codes = url[-24:]
    
    # Check if we have exactly 24 characters
    if len(color_codes) != 24:
        raise ValueError("Invalid URL format. Expected 24 characters of color codes.")
    
    # Split the color codes into a list of 4 colors
    colors = [color_codes[i:i+6] for i in range(0, 24, 6)]
    
    return colors