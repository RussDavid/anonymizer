import pathlib
import re
import traceback
import string
import argparse
import configparser
from time import perf_counter
from random import randint, choice
import pandas as pd
import faker

class AnonymizerConfigurator():
    NAMED_GROUP_PATTERN = re.compile(r'\(\?P<\w*>.+\)')

    def __init__(self, _field_pattern_mapping,
                 _custom_replacement_values,
                 _no_of_values_to_generate,
                 _faker_seed) -> pd.Series:
        self.field_pattern_mapping = _field_pattern_mapping
        self.custom_replacement_values = _custom_replacement_values
        self.no_of_values_to_generate = _no_of_values_to_generate
        self.faker_seed = _faker_seed
        self.__validate_regex_pattern()
        self.__build_replacement_value_lists()

    def __build_replacement_value_lists(self):
        print('Generating values for replacement lists')
        self.first_name_values, self.last_name_values = [], []
        self.house_no_values, self.street_values = [], []
        self.city_values, self.email_address_values = [], []

        fake = faker.Faker()
        faker.Faker.seed(self.faker_seed)
        start_time = perf_counter()
        for _ in range(self.no_of_values_to_generate):
            self.first_name_values.append(fake.first_name())
            self.last_name_values.append(fake.last_name())
            self.email_address_values.append(fake.email())
            self.house_no_values.append(fake.building_number())
            self.street_values.append(fake.street_address())
            self.city_values.append(fake.city())
        end_time = perf_counter()
        print(f'Took {end_time - start_time} seconds to generate replacement lists')


        self.replacement_values = {
            'fname': self.first_name_values,
            'lname': self.last_name_values,
            'email': self.email_address_values,
            'house_no': self.house_no_values,
            'street_name': self.street_values,
            'city': self.city_values
        }

        if self.custom_replacement_values is not None:
            for regex_group_key in self.custom_replacement_values:
                self.replacement_values[regex_group_key] = \
                    self.custom_replacement_values[regex_group_key]

    def __validate_regex_pattern(self):
        for pattern in self.field_pattern_mapping.values():
            if re.search(pattern=self.NAMED_GROUP_PATTERN, string=pattern) is None:
                raise re.error(msg=f'The Regular Expression: {pattern} is invalid, '
                               'it does not contain a named group')

    def anonymize_record(self, _row):
        anon = RecordAnonymizer(row=_row,
                            replacement_map=self.replacement_values,
                            field_pattern_map=self.field_pattern_mapping)
        return anon.randomize_fields()


class RecordAnonymizer():
    LETTERS_LOWER = string.ascii_lowercase
    LETTERS_UPPER = string.ascii_uppercase

    def __init__(self, row, replacement_map, field_pattern_map) -> None:
        # TODO: move replacement_dict and field_pattern_dict init into
        # a class method
        self.row = row
        self.replacement_value_map = replacement_map
        self.field_pattern_map = field_pattern_map
        self.validated_randomization_pattern = None

        self.first_name, self.last_name = None, None
        self.email_address, self.phone = None, None
        self.city, self.street, self.post_code = None, None, None

        self.function_map = {
            'digits': self.__randomize_digits,
            'chars': self.__randomize_chars,
            'fname': {
                'function': self.__get_anonymized_value,
                'replacement_list': self.replacement_value_map['fname'],
                'current_value': None
            },
            'lname': {
                'function': self.__get_anonymized_value,
                'replacement_list': self.replacement_value_map['lname'],
                'current_value': None
            },
            'email': {
                'function': self.__get_anonymized_value,
                'replacement_list': self.replacement_value_map['email'],
                'current_value': None
            },
            'street_name': {
                'function': self.__get_anonymized_value,
                'replacement_list': self.replacement_value_map['street_name'],
                'current_value': None
            },
            'city': {
                'function': self.__get_anonymized_value,
                'replacement_list': self.replacement_value_map['city'],
                'current_value': None
            },
            'post_code': self.__get_random_postcode,
            'phone': self.__get_random_nz_phone
        }

        if self.replacement_value_map is not None:
            for replacement_list_key in self.replacement_value_map:
                self.function_map[replacement_list_key] = {
                    'function': self.__get_anonymized_value,
                    'replacement_list': self.replacement_value_map[replacement_list_key],
                    'current_value': None
                }

    def __get_anonymized_value(self, source_list):
        return choice(source_list)
        # return source_list[randint(0, len(source_list) - 1)]

    def __randomize_digits(self, digits):
        new_digits = ''
        for _ in range(len(digits)):
            new_digits = new_digits + str(randint(0, 9))
        return new_digits

    def __randomize_chars(self, chars):
        new_word = ''
        for char in chars:
            if char.islower():
                new_word = new_word + choice(self.LETTERS_LOWER)
            elif char.isupper():
                new_word = new_word + choice(self.LETTERS_UPPER)
        return new_word

    def __get_random_postcode(self, _):
        if self.post_code is None:
            self.post_code = str(randint(1000, 9999))
        return self.post_code

    def __get_random_nz_phone(self, _):
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
                    # TODO: add option to replace empty values?
                    if match_group_value in [None, '', 'nan']:
                        continue

                    # From the function map get a function or dictionary containing
                    # the relevant function to anonoymize this regex group value
                    # Randomized values that are used across multiple columns are stored
                    match_group_randomizer = self.function_map[match_group_name]
                    if match_group_randomizer.isinstance(dict):
                        if match_group_randomizer['current_value'] is None:
                            randomizer_function = match_group_randomizer['function']
                            random_replacement_values = match_group_randomizer['replacement_list']
                            randomized_value = randomizer_function(random_replacement_values)
                            match_group_randomizer['current_value'] = randomized_value
                        else:
                            randomized_value = match_group_randomizer['current_value']
                    else: # This type of match group does not persist values across columns
                        randomized_value = match_group_randomizer(match_group_value)

                    self.row[field] = self.row[field].replace(match_group_value, randomized_value)
        return self.row


if __name__ == '__main__':
    pattern_file = pathlib.Path('patterns.ini')
    data_file = pathlib.Path('data.csv')

    parser = argparse.ArgumentParser(
        prog='Basic Data Anonymizer',
        description='Use this script to replace sensitive data with randomized data.',
    )
    parser.add_argument('--pattern-file-path', '-pf',
                        type=pathlib.Path,
                        default=pattern_file,
                        help='The path to the file that contains the mapping of '\
                            'fields to patterns as well as the regex pattern definitions. '\
                            'Default Path: .\\patterns.txt')
    parser.add_argument('--data-file-path', '-df',
                        type=pathlib.Path,
                        default=data_file,
                        help='The path to the file that contains the data the anonymized. '\
                            'Default Path: .\\data.csv')
    parser.add_argument('--generate-values', '-gv',
                        type=int,
                        default=10000,
                        help='The number of random replacement values each replacement list '\
                            'should contain.  Default: 10,000')
    parser.add_argument('--faker-seed', '-fs',
                        type=int,
                        default=0,
                        help='The seed value that Faker uses. Changing this will change which '\
                            'values are selected to be populated into the replacement lists. '\
                            'Default: 0')
    args = parser.parse_args()

    if str(args.pattern_file_path) != str(pattern_file):
        pattern_file = args.pattern_file_path
    if str(args.data_file_path) != str(data_file):
        data_file = args.data_file_path

    try:
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(pattern_file)

        if 'Regex_Patterns' not in config:
            raise configparser.NoSectionError('Regex_Patterns')
        elif 'Field_Mapping' not in config:
            raise configparser.NoSectionError('Field_Mapping')

        # Combine the two sections in the configuration file into one dictionary
        # of the structure: field_name: regular_expression_string
        # e.g. 'first_name': '(?<fname>/w+)
        # Get the name of the associated pattern for this field contained in
        # the [Regex_Patterns] section
        field_to_pattern = {}
        for key in config['Field_Mapping']:
            pattern_name = config['Field_Mapping'][key]
            regex_pattern = config['Regex_Patterns'][pattern_name]
            field_to_pattern[key] = regex_pattern

        # Get the user created lists of replacement values from the config file
        # This is read as a string which then needs to be converted to a list
        user_replacement_values = {}
        path_regex = re.compile(pattern=r'^(((\w+:*|\d+)?(\\|\/))*(\w+|\d+))+\.(csv|txt)\s*$',
                                flags=re.IGNORECASE)
        if 'Replacement_Values' in config:
            for replacement_key in config['Replacement_Values']:
                replacement_values = config['Replacement_Values'][replacement_key]
                # If the replacement value is a path instead of a list
                # then the replacement values must be loaded from that file
                if re.match(path_regex, replacement_values):
                    replacement_value_file = pathlib.Path(replacement_values)
                    replacement_df = pd.read_csv(replacement_value_file, header=None)
                    file_values = replacement_df.iloc[0].values
                    user_replacement_values[replacement_key] = file_values
                else:
                    replacement_values = replacement_values.removeprefix('[').removesuffix(']')
                    replacement_values = replacement_values.replace(', ', ',').split(',')
                    user_replacement_values[replacement_key] = replacement_values

        df = pd.read_csv(data_file)
        df = df.astype(str)

        print('Finished initial configuration')
        print('Creating Anonymizer object')

        anonymizer = AnonymizerConfigurator(field_to_pattern, user_replacement_values,
                                            args.generate_values, args.faker_seed)
        
        df_anon = df.apply(lambda x: anonymizer.anonymize_record(x), axis=1)
        
        print('Anonymized output:')
        print(df_anon)
    except configparser.NoSectionError as error:
        print(traceback.format_exc())
        print(f'{error}\nPattern config file must both [Regex_Patterns] '\
              'and [Field_Mapping] sections')
    except re.error as error:
        print(traceback.format_exc())
        print(error)
    except FileNotFoundError as error:
        print(traceback.format_exc())
        print(f'The file {error.filename} could not be found.\n'
              'Check that the file exists and the path is valid.')
    except KeyError as error:
        print(traceback.format_exc())
        print(f'An error occured, KeyError: {error}')
        print('This error is most likely caused due to incorrect mapping between\n'
              'the [Field_Mapping] in the config file and the columns present\n'
              'in the data file. The names of the fields defined in the [Field_Mapping]\n'
              'must match the names of the columns in the data file.\n'
              'Field and column names are case-sensitive.')
    except Exception as e:
        print(traceback.format_exc())
        print(e)
        print('Some other exception occurred.')
        