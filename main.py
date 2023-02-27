import pathlib
import re
import traceback
import argparse
import configparser
import logging
import time
import pandas as pd
import anonymizer


if __name__ == '__main__':
    logger = logging.getLogger('main')
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('anonymizer.log')
    console_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)

    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    pattern_file = pathlib.Path('demo', 'demo_config.ini')
    data_file = pathlib.Path('demo', 'demo_data.csv')
    output_file = pathlib.Path('demo', 'output.csv')

    logger.info('-------------------------------')
    logger.info('Data Anonymizer Started')
    logger.info(time.asctime(time.localtime()))
    logger.info('-------------------------------')

    parser = argparse.ArgumentParser(
        prog='Basic Data Anonymizer',
        description='Use this script to replace sensitive data with randomized data.'
    )

    parser.add_argument('--pattern-file-path', '-pfp',
                        type=pathlib.Path,
                        default=pattern_file,
                        help='The path to the file that contains the mapping of '
                        'fields to patterns as well as the regex pattern definitions. '
                        'Default Path: .\\patterns.txt')
    parser.add_argument('--data-file-path', '-dfp',
                        type=pathlib.Path,
                        default=data_file,
                        help='The path to the file that contains the data the anonymized. '
                        'Default Path: .\\data.csv')
    parser.add_argument('--output-file-path', '-ofp',
                        type=pathlib.Path,
                        default=output_file,
                        help='The path and name of the file the anonymized data will be '
                        'saved to. Default Path: .\\demo\\output.csv')
    parser.add_argument('--generate-values', '-gv',
                        type=int,
                        default=10000,
                        help='The number of random replacement values each replacement list '
                        'should contain.  Default: 10,000')
    parser.add_argument('--faker-seed', '-fs',
                        type=int,
                        default=0,
                        help='The seed value that Faker uses. Changing this will change which '
                        'values are selected to be populated into the replacement lists. '
                        'Default: 0')
    parser.add_argument('--replace-empty-values', '-rev',
                        action='store_true',
                        help='If this argument is passed then empty values in the input data '
                        'will be populated with anonymized data. By default blank values are not '
                        'populated with anything, left are left empty.')
    parser.add_argument('--column-name-suffix', '-cns',
                        default=None,
                        type=str,
                        help='Add this value to the end of anonymized columns in output data.')

    args = parser.parse_args()

    argument_options = {
        'generate_values': args.generate_values,
        'faker_seed': args.faker_seed,
        'replace_empty': args.replace_empty_values,
        'column_suffix': args.column_name_suffix
    }

    logger.info(f'Using pattern file located at path: {str(args.pattern_file_path)}')
    logger.info(f'Using output file located at path: {str(args.output_file_path)}\n')
    logger.info(f'Using data file located at path: {str(args.data_file_path)}')

    try:
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(args.pattern_file_path)

        if 'Regex_Patterns' not in config:
            raise configparser.NoSectionError('Regex_Patterns')
        elif 'Field_Mapping' not in config:
            raise configparser.NoSectionError('Field_Mapping')

        # Combine the two sections in the configuration file into one dictionary
        # of the structure: field_name: regular_expression_string
        # e.g. 'first_name': '(?<fname>/w+)
        # Get the name of the associated pattern for this field contained in
        # the [Regex_Patterns] section
        logger.info('Mapping fields to patterns')
        field_to_pattern = {}
        for field_name in config['Field_Mapping']:
            pattern_name = config['Field_Mapping'][field_name]
            regex_pattern = config['Regex_Patterns'][pattern_name]
            field_to_pattern[field_name] = regex_pattern
        logger.debug('field_to_pattern dictionary: %s', field_to_pattern)

        # The path_regex pattern matches paths such as:
        # C:/files/list.csv | /sensitive/data/people.txt
        # data.csv | \backward\slashes\also\work.csv
        user_replacement_values = {}
        path_regex = re.compile(pattern=r'^(((\w+:*|\d+)?(\\|\/))*(\w+|\d+))+\.(csv|txt)\s*$',
                                flags=re.IGNORECASE)
        # Get the user created lists of replacement values from the config file
        # This is read as a string which then needs to be converted to a list.
        if 'Replacement_Values' in config:
            logger.info('Custom replacement values are defined')
            for replacement_key in config['Replacement_Values']:
                replacement_values = config['Replacement_Values'][replacement_key]
                # The replacement value can be a path to a CSV file containing a
                # list of replacement values.
                if re.match(path_regex, replacement_values):
                    replacement_value_file = pathlib.Path(replacement_values)
                    replacement_df = pd.read_csv(replacement_value_file, header=None)
                    file_values = replacement_df.iloc[0].values
                    user_replacement_values[replacement_key] = file_values

                    logger.info('Loaded %d values for field: %s, in file: %s',
                                len(file_values), replacement_key, str(replacement_value_file.name))
                else:
                    replacement_values = replacement_values.removeprefix('[').removesuffix(']')
                    replacement_values = replacement_values.replace(', ', ',').split(',')
                    user_replacement_values[replacement_key] = replacement_values

        if not args.data_file_path.is_file():
            raise FileNotFoundError
        elif args.data_file_path.suffix == '.csv':
            df = pd.read_csv(args.data_file_path)
        elif args.data_file_path.suffix == '.xslx':
            df = pd.read_excel(args.data_file_path)
        else:
            raise Exception(f'Invalid file format {args.data_file_path.suffix}')

        logger.info(f'Input data has {len(df.columns)} columns and {len(df)} rows\n')
        df = df.astype(str)
        logger.info('Loaded all files successfully, beginning anonymization')

        anon_config = anonymizer.AnonymizerConfigurator(
            field_pattern_mapping=field_to_pattern,
            custom_replacement_values=user_replacement_values,
            config_options=argument_options)

        df_anon = df.apply(lambda x: anon_config.anonymize_record(x), axis=1)

        # If a column suffix was passed, append the suffix to all the column names
        # that were anonymized
        if argument_options['column_suffix'] is not None:
            for field in field_to_pattern:
                print(field)
                df_anon = df_anon.rename(columns={field: field + argument_options['column_suffix']})

        logger.info(f'Completed anonymization, writing to file: {args.output_file_path}')
        df_anon = df_anon.replace('nan', '')
        df_anon.to_csv(args.output_file_path, index=False)
        print('Anonymized output:')
        print(df_anon)
    except configparser.NoSectionError as error:
        print(traceback.format_exc())
        print(f'{error}\nPattern config file must both [Regex_Patterns] '
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
        print('Exception Occured:')
        print(e)
