import re
import string
import logging
import time
from random import randint, choice
import pandas as pd
import faker

logger = logging.getLogger('main.anonymizer')
logger.name = logger.name.replace('main.', '')


class AnonymizerConfigurator():
    NAMED_GROUP_PATTERN = re.compile(r'\(\?P<\w*>.+\)')

    def __init__(self, field_pattern_mapping,
                 custom_replacement_values,
                 config_options) -> pd.Series:
        self.field_pattern_mapping = field_pattern_mapping
        self.custom_replacement_values = custom_replacement_values
        self.no_of_values_to_generate = config_options['generate_values']
        self.faker_seed = config_options['faker_seed']
        self.replace_empty = config_options['replace_empty']
        self.__validate_regex_patterns()
        self.__build_replacement_value_lists()

    def __build_replacement_value_lists(self):
        logger.info('Generating values for replacement lists')
        self.first_name_values, self.last_name_values = [], []
        self.house_no_values, self.street_values = [], []
        self.city_values, self.email_address_values = [], []

        fake = faker.Faker()
        faker.Faker.seed(self.faker_seed)
        start_time = time.perf_counter()
        for _ in range(self.no_of_values_to_generate):
            self.first_name_values.append(fake.first_name())
            self.last_name_values.append(fake.last_name())
            self.email_address_values.append(fake.email())
            self.house_no_values.append(fake.building_number())
            self.street_values.append(fake.street_address())
            self.city_values.append(fake.city())
        end_time = time.perf_counter()

        self.replacement_values = {
            'fname': self.first_name_values,
            'lname': self.last_name_values,
            'email': self.email_address_values,
            'house_no': self.house_no_values,
            'street_name': self.street_values,
            'city': self.city_values
        }
        logger.debug(f'Took {end_time - start_time:.{2}} seconds to generate '
                     f'{self.no_of_values_to_generate * len(self.replacement_values)} '
                     'replacement list values')

        if self.custom_replacement_values is not None:
            for regex_group_key in self.custom_replacement_values:
                self.replacement_values[regex_group_key] = \
                    self.custom_replacement_values[regex_group_key]

    def __validate_regex_patterns(self):
        for pattern in self.field_pattern_mapping.values():
            if re.search(pattern=self.NAMED_GROUP_PATTERN, string=pattern) is None:
                logger.error(f'Invalid regex pattern: {pattern}')
                raise re.error(msg=f'The Regular Expression: {pattern} is invalid, '
                               'it does not contain a named group')

    def anonymize_record(self, row):
        RecordAnonymizer.initialize_record_anonymizer(replacement_value_map=self.replacement_values,
                                                      field_pattern_map=self.field_pattern_mapping,
                                                      replace_empty_values=self.replace_empty)
        anon = RecordAnonymizer(row=row)
        return anon.randomize_fields()


class RecordAnonymizer():
    LETTERS_LOWER = string.ascii_lowercase
    LETTERS_UPPER = string.ascii_uppercase

    replacement_value_map = []
    field_pattern_map = []
    replace_empty_values = None

    @classmethod
    def initialize_record_anonymizer(cls, replacement_value_map, field_pattern_map,
                                     replace_empty_values):
        cls.replacement_value_map = replacement_value_map
        cls.field_pattern_map = field_pattern_map
        cls.replace_empty_values = replace_empty_values

    def __init__(self, row, ) -> None:
        self.row = row
        self.first_name, self.last_name = None, None
        self.email_address, self.phone = None, None
        self.city, self.street, self.post_code = None, None, None

        self.function_map = {
            'digits': self._randomize_digits,
            'chars': self._randomize_chars,
            'fname': {
                'function': self._get_anonymized_value,
                'replacement_list': self.replacement_value_map['fname'],
                'current_value': None
            },
            'lname': {
                'function': self._get_anonymized_value,
                'replacement_list': self.replacement_value_map['lname'],
                'current_value': None
            },
            'email': {
                'function': self._get_anonymized_value,
                'replacement_list': self.replacement_value_map['email'],
                'current_value': None
            },
            'street_name': {
                'function': self._get_anonymized_value,
                'replacement_list': self.replacement_value_map['street_name'],
                'current_value': None
            },
            'city': {
                'function': self._get_anonymized_value,
                'replacement_list': self.replacement_value_map['city'],
                'current_value': None
            },
            'post_code': self._get_random_postcode,
            'phone': self._get_random_nz_phone
        }

        if self.replacement_value_map is not None:
            for replacement_list_key in self.replacement_value_map:
                self.function_map[replacement_list_key] = {
                    'function': self._get_anonymized_value,
                    'replacement_list': self.replacement_value_map[replacement_list_key],
                    'current_value': None
                }

    def _get_anonymized_value(self, source_list):
        return choice(source_list)

    def _randomize_digits(self, digits):
        new_digits = ''
        for _ in range(len(digits)):
            new_digits = new_digits + str(randint(0, 9))
        return new_digits

    def _randomize_chars(self, chars):
        new_word = ''
        for char in chars:
            if char.islower():
                new_word = new_word + choice(self.LETTERS_LOWER)
            elif char.isupper():
                new_word = new_word + choice(self.LETTERS_UPPER)
        return new_word

    def _get_random_postcode(self, _):
        if self.post_code is None:
            self.post_code = str(randint(1000, 9999))
        return self.post_code

    def _get_random_nz_phone(self, _):
        if self.phone is None:
            self.phone = '642' + str(randint(10000000, 99999999))
        return self.phone

    # Loop over each field in field to pattern mapping
    # Get the column value from the Pandas series
    # Check if the column value contains a match to the regex pattern
    def randomize_fields(self):
        for field, pattern in self.field_pattern_map.items():
            match = re.search(pattern, self.row[field])
            if match:
                match_groups = match.groupdict()
                for match_group_name, match_group_value in match_groups.items():
                    if not self.replace_empty_values and match_group_value in [None, '', 'nan']:
                        continue

                    # From the function map get a function or dictionary containing
                    # the relevant function to anonoymize this regex group value
                    # Randomized values that are used across multiple columns are stored
                    match_group_randomizer = self.function_map[match_group_name]
                    if isinstance(match_group_randomizer, dict):
                        if match_group_randomizer['current_value'] is None:
                            randomizer_function = match_group_randomizer['function']
                            random_replacement_values = match_group_randomizer['replacement_list']
                            randomized_value = randomizer_function(random_replacement_values)
                            match_group_randomizer['current_value'] = randomized_value
                        else:
                            randomized_value = match_group_randomizer['current_value']
                    else:  # This type of match group does not persist values across columns
                        randomized_value = match_group_randomizer(match_group_value)

                    self.row[field] = self.row[field].replace(match_group_value, randomized_value)
        return self.row
