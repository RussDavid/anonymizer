import pathlib
import re
import traceback
import string
import argparse
import configparser
from random import randint, choice
import pandas as pd
import faker

class AnonymizerWrapper():
    first_names, last_names, email_addresses = [], [], []
    house_nos, streets, cities = [], [], []
    field_pattern_dict = {}
    
    @classmethod
    def init_anonymizer(cls, _field_pattern_dict):
        cls.field_pattern_dict = _field_pattern_dict
        
        fake = faker.Faker()
        faker.Faker.seed(0)
        
        for _ in range(5000):
            cls.first_names.append(fake.first_name())
            cls.last_names.append(fake.last_name())
            cls.email_addresses.append(fake.email())
            cls.house_nos.append(fake.building_number())
            cls.streets.append(fake.street_address())
            cls.cities.append(fake.city())
            
            
    def anonymize_record(cls, field_name):
        try:
            replacement_dict = {
                'fnames': cls.first_names,
                'lnames': cls.last_names,
                'emails': cls.email_addresses,
                'house_nums': cls.house_nos,
                'streets': cls.streets,
                'cities': cls.cities
            }
            
            anon = Anonymizer(row=field_name,  
                              replacement_dict=replacement_dict,
                              field_pattern_dict=cls.field_pattern_dict)
            return anon.randomize_fields()
        except Exception as err:
            print(err)
            print(traceback.format_exc())
        
        
class Anonymizer():
    NAMED_GROUP_PATTERN = re.compile(r'\(\?P<\w*>.+\)')
    LETTERS_LOWER = string.ascii_lowercase
    LETTERS_UPPER = string.ascii_uppercase
    
    def __init__(self, row, replacement_dict, field_pattern_dict) -> None:
        self.row = row
        self.replacement_dict = replacement_dict
        self.field_pattern_dict = field_pattern_dict
        self.validated_randomization_pattern = None
        
        self.first_name, self.last_name = None, None
        self.email_address, self.phone = None, None 
        self.city, self.street, self.post_code = None, None, None
        
        self.function_map = {
            'digits': self.__randomize_digits,
            'chars': self.__randomize_chars,
            'fname': self.__get_random_first_name,
            'lname': self.__get_random_last_name,
            'email': self.__get_random_email,
            'street_name': self.__get_random_street,
            'city': self.__get_random_city,
            'post_code': self.__get_random_postcode,
            'phone': self.__get_random_nz_phone
        }

        self.__validate_regex_pattern()
        
    def __validate_regex_pattern(self):
        for pattern in self.field_pattern_dict.values():
            if re.search(pattern=self.NAMED_GROUP_PATTERN, string=pattern) is None:
                raise re.error(msg=f'The Regular Expression: {pattern} is invalid, it does not contain a named group')

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
    
    def __get_anonymized_value(self, source_list):
        return source_list[randint(0, len(source_list) - 1)]
        
    def __get_random_first_name(self, _):
        if self.first_name is None:
            self.first_name = self.__get_anonymized_value(self.replacement_dict['fnames'])
        return self.first_name
        
    def __get_random_last_name(self, _):
        if self.last_name is None:
            self.last_name = self.__get_anonymized_value(self.replacement_dict['lnames'])
        return self.last_name
    
    def __get_random_email(self, _):
        if self.email_address is None:
            self.email_address = self.__get_anonymized_value(self.replacement_dict['emails'])
        return self.email_address
    
    def __get_random_city(self, _):
        if self.city is None:
            self.city = self.__get_anonymized_value(self.replacement_dict['cities'])
        return self.city
    
    def __get_random_street(self, _):
        if self.street is None:
            self.street = self.__get_anonymized_value(self.replacement_dict['streets'])
        return self.street
    
    def __get_random_postcode(self, _):
        if self.post_code is None:
            self.post_code = str(randint(1000, 9999))
        return self.post_code
    
    def __get_random_nz_phone(self, _):
        if self.phone is None:
            self.phone = '642' + str(randint(10000000, 99999999))
        return self.phone         
    
    def randomize_fields(self):
        for field, pattern in self.field_pattern_dict.items():
            match = re.search(pattern, self.row[field])
            if match:
                match_dict = match.groupdict()
                
                for key in match_dict:
                    if match_dict[key] in [None, '']:
                        continue
                    
                    randomizer_function = self.function_map[key]
                    randomized_value = randomizer_function(match_dict[key])
                    self.row[field] = self.row[field].replace(match_dict[key], randomized_value)
            else:
                pass
                # print(f'No match found for expression: {pattern} on field {field} for value {self.row[field]}')
                
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
                        help='The path to the file that contains the mapping of fields to patterns '\
                            'as well as the Regular Expression patterns definitions. Default Path: .\patterns.txt')
    parser.add_argument('--data-file-path', '-df',
                        type=pathlib.Path,
                        default=data_file,
                        help='The path to the file that contains the data the anonymized. '\
                            'Default Path: .\data.csv')
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
        # 'first_name': '(?<fname>/w+)
        # Get the name of the associated pattern for this field contained in
        # the [Regex_Patterns] section
        field_to_pattern = {}
        for key in config['Field_Mapping']:
            pattern_name = config['Field_Mapping'][key]
            regex_pattern = config['Regex_Patterns'][pattern_name]
            field_to_pattern[key] = regex_pattern
            
        df = pd.read_csv(data_file)
        df = df.astype(str)
        
        print('Finished initial configuration')
    except configparser.NoSectionError as e:
        print(f'{e}\nPattern config file must both [Regex_Patterns] and [Field_Mapping] sections')
        print(traceback.format_exc())
    except Exception as e:
        print(e)
        print(traceback.format_exc())
    
    try:
        anonymizer = AnonymizerWrapper()
        anonymizer.init_anonymizer(field_to_pattern)
        
        df_anon = df.apply(lambda x: anonymizer.anonymize_record(x), axis=1)
        print(df_anon)
    except Exception as e:
        print(traceback.format_exc())