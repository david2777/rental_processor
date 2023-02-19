import unittest

from rp import utils
from rp import constants as c

header = ["Listing ID (MLS#)", "Sub Type", "St#", "St Name", "City", "PostalCode", "Br/Ba", "DepositKey",
          "DepositOther", "DepositPets", "DepositSecurity", "List Price", "Price Per Square Foot", "Sqft",
          "Yr Built", "Garage Spaces", "PetsAllowed", "LaundryFeatures", "Furnished", "Terms", "List Office Phone"]


class TestUpdateHeader(unittest.TestCase):
    def test_update_columns(self):
        check = utils.update_columns(header)
        self.assertTrue(check)
        self.assertEqual(c.MLS, 0)
        self.assertEqual(c.TYP, 1)
        self.assertEqual(c.ST_NUMBER, 2)
        self.assertEqual(c.ST_NAME, 3)
        self.assertEqual(c.CITY, 4)
        self.assertEqual(c.ZIP_CODE, 5)
        self.assertEqual(c.BEDS_BATH, 6)
        self.assertEqual(c.RENT, 11)
        self.assertEqual(c.SQFT, 13)
        self.assertEqual(c.PETS, 16)


if __name__ == '__main__':
    unittest.main()
