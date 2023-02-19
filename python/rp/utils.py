from rp import logger
from rp import constants as c


def update_columns(header_row: list[str]) -> bool:
    """Updates the constants column numbers using the header row from the input csv file. This way when the csv file
    format changes the script will automatically compensate for most changes. 
    
    Args:
        header_row (list[str]): A list of string from the header row of the input csv file.

    Returns:
        bool: Returns True if all columns were successfully updated, False if not. 
    """
    for i, item in enumerate(header_row):
        item = item.lower()
        if 'mls' in item:
            c.MLS = i
        elif 'type' in item:
            c.TYP = i
        elif 'city' in item:
            c.CITY = i
        elif 'postal' in item:
            c.ZIP_CODE = i
        elif 'list price' in item:
            c.RENT = i
        elif 'sqft' in item:
            c.SQFT = i
        elif 'pets' in item:
            c.PETS = i
        elif 'st name' in item:
            c.ST_NAME = i
        elif 'st#' in item:
            c.ST_NUMBER = i
        elif 'br' in item and 'ba' in item:
            c.BEDS_BATH = i

    check = []
    all_cols = {'MLS': c.MLS, "Type": c.TYP, 'Street Number': c.ST_NUMBER, 'Street Name': c.ST_NAME, 'City': c.CITY,
                'ZIP Code': c.ZIP_CODE, 'Beds/Baths': c.BEDS_BATH, 'Rent': c.RENT, 'SQFT': c.SQFT, 'Pets': c.PETS}
    logger.debug('Column Values')
    for name, value in all_cols.items():
        check.append(value != -1)
        logger.debug('\t%s: %s', name, value)

    return all(check)
