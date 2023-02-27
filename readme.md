# Configurable Data Anonymizer

Replace sensitive data with randomly generated data.

Features:
- Define custom patterns to detect sensitive
- Input custom replacement values lists
- Create mappings of columns to replacement patterns
- Using the Faker package generate replacement values. Replacement value types built in:
    - First names
    - Last names
    - Email addresses
    - Street addresses
    - Cities

## Sensitive Input Data:
<table>
    <tr>
        <th>first_name</th>
        <th>last_name</th>
        <th>user_id</th>
        <th>email_address</th>
        <th>contact_string</th>
    </tr>
    <tr>
        <td>John</td>
        <td>Smith</td>
        <td>12345</td>
        <td>john@smith.com</td>
        <td>john@smith.com:123 Main Street:Auckland:0632</td>
    </tr>
    <tr>
        <td>Jane</td>
        <td>Doe</td>
        <td>54321</td>
        <td>jane@mail.com</td>
        <td>jane@mail.com:321 North Avenue:Sydney:5511</td>
    </tr>
</table>

## Anonymized Output Data:

<table>
    <tr>
        <th>first_name</th>
        <th>last_name</th>
        <th>user_id</th>
        <th>email_address</th>
        <th>contact_string</th>
    </tr>
    <tr>
        <td>Joshua</td>
        <td>Brown</td>
        <td>31561</td>
        <td>tree15@example.com</td>
        <td>tree15@example.com:123 Main Street:Auckland:0632</td>
    </tr>
    <tr>
        <td>Mary</td>
        <td>Herman</td>
        <td>81308</td>
        <td>ball76@example.com</td>
        <td>ball76@example.com:321 North Avenue:Sydney:5511</td>
    </tr>
</table>

---

# Installation

To run this script a Python 3.7 or later must be installed and a Python environment with Pandas and Faker packages installed is required.

## Installation Steps:
Ensure Python 3.7 or later is by entering the following command in a terminal:
1. `python -V` If an error message is displayed instead of the version of Python 
then Python is not installed. <br>
Download and install Python first: [Download Python](https://www.python.org/downloads/)

Once Python is installed create a new Python virtual environment and activate it from a terminal:
1. `python -m venv anon_env`<br><br>
2. `.\anon_env\Scripts\activate`

Install the required packages with pip using the `requirements.txt` file:
1. `pip install -r requirements.txt`

---

# Configuration and Data Files

## Creating a Config File

A config file is used to define regular expressions, create mappings between regular expressions and columns in the input data, and define custom replacement values. There are three sections defined in the config file:
- `[Regex_Patterns]` define a key for the regular expression and pattern for this key. This section is **required**.
- `[Field_Mapping]` define a mapping between the column names in the input data and the regular expressions defined in the `[Regex_Patterns]` section which will be used to match the senstive data in the specified column. This section is **required**.
- `[Replacement_Values]` define lists or paths to CSV files containing lists of replacement values. These values are subsituted in for the senstive data when it is matched by the patterns defined in the `[Regex_Patterns]` section. This section is **optional**.

### Example Configuration File

```
[Regex_Patterns]
firstName_pattern = (?P<fname>.*)
lastName_pattern = (?P<lname>.*)
month_pattern = (?P<month_values>.*)
username_pattern = (?P<username_values>\w+\d+)

[Field_Mapping]
first_name = firstName_pattern
last_name = lastName_pattern
month = month_pattern
username = username_pattern

[Replacement_Values]
month_values = [January, February, March, April, May, June, July, August, September, October, November, December]
username_values = demo/demo_username_list.csv
```

## Input Data Format

Input data files that are to be anonymized must be comma seperated values in either CSV or XLSX format. 

### Example Input Data File

```
first_name,last_name,month,username,active_date
Ben,McCollins,January,ben123,10/05/2022
```

<table>
    <tr>
        <th>first_name</th>
        <th>last_name</th>
        <th>month</th>
        <th>username</th>
        <th>active_date</th>
    </tr>
    <tr>
        <td>Ben</td>
        <td>McCollins</td>
        <td>January</td>
        <td>ben123</td>
        <td>10/05/2022</td>
    </tr>
</table>

---

# How To: Defining Custom Regular Expressions 

In the `[Regex_Patterns]` section of the configuration file custom regular expressions can be defined. User defined patterns **must contain at least one named group**. The named group corresponds to a list of values defined in the `[Replacement_Values]` section that are used to replace the senstive matched data.

## Custom Regular Expression Example

In this example we will take the input table below and replace all the `login_username` values that begin with a letter and end with a digit and replace them with our own custom defined usernames.

### Sample Input Data `data.csv`:

<table>
    <tr>
        <th>USER_ID</th>
        <th>LOGIN_USERNAME</th>
    </tr>
    </tr>
        <td>1</td>
        <td>ben123</td>
    </tr>
    </tr>
        <td>2</td>
        <td>jen321</td>
    </tr>
    </tr>
        <td>3</td>
        <td>987jim</td>
    </tr>
</table>

### Create a Regular Expression

First create a file called `config.ini`, all configuration detail will be added to this file.

We now need to create a regular expression that can match a username that starts with a letter and ends with a digit, we define the pattern: `^\w+\d+$`. The breakdown of this pattern is:

1. `^` confirms that this is the start of the line/text, there are no prefixing characters
2. `\w+` means we want to match any letter `\w` at least one or more times `+`
3. `\d+` means we want to match any digit `\d` at least one or more times `+`
4. `$` confirms that this is the end of the line/text and that there are suffixing characters

This will match values such as: ben123, jim321, KEV1<br>
But will not match values such as: 123Ben123, Jim, 3212, Doe321a

Once we have defined the pattern that will match the data we want anonymized we wrap this pattern in a named group, the name of this group corresponds to the name of the replacement list values we define. 

`^\w+\d+$` now becomes: `(?<username_vals>^\w+\d+$)` and we define this in our configuration file under the `[Regex_Patterns]` sections:

```
[Regex_Patterns]
username_pattern = (?<username_vals>^\w+\d+$)
```

### Create a Mapping Between Columns in Data and Regular Expressions

Now that we have defined a pattern to match the data in our `login_username` column that we want anonymized we need to add the mapping between column and pattern to our configuration file. The key of the `[Field_Mapping]` section is the column name in our data (**column names are case-sensitive**) and the value is the key of our regular expression we defined in the `[Regex_Patterns]` section. Our configuration file now becomes:

```
[Regex_Patterns]
username_pattern = (?<username_vals>^\w+\d+$)

[Field_Mapping]
LOGIN_USERNAME = username_pattern
```

### Define a List of Replacement Values

We need to create a list of dummy usernames that can be used to replace the sensitive data in LOGIN_USERNAME column. To do this we add the `[Replacement_Values]` section to our configuration file.

The key in the `[Replacement_Values]` section is the name of the named group we defined in our regular expression earlier: `(?<username_vals>...)` the value is either a list of replacement values (format: `[A, B, C, ...]`) or a Path to a CSV file containing the values.

```
[Regex_Patterns]
username_pattern = (?<username_vals>^\w+\d+$)

[Field_Mapping]
LOGIN_USERNAME = username_pattern

[Replacement_Values]
username_vals = [User123, User321, User999, User111]
```

### Executing the Anonymization Process

Now that we have set up our configuration file we can begin the anonymization process.
1. Open a terminal and ensure that a Python environment containing Pandas and Faker packages is activated.
2. Execute the main.py script and pass in a Path to the data file and a Path to the configuration file: `python main.py --pattern-file-path c:/files/config.ini --data-file-path c:/files/data.csv --output-file-path c:/files/output.csv'`
    - `--pattern-file-path [PATH]` a Path to the configuration file `config.ini` that we created
    - `--data-file-path [PATH]` a Path to the file that contains the data that we are anonymizing (the input data)
    - `--output-file-path [PATH]` a Path to which the anonymized output data should be saved

The anonymization process will run and create a file at the Path specified using the `--output-file-path` argument. The final results of anonymization are:

<table>
    <tr>
        <th>Input Sensitive Data (data.csv)</th>
        <th>Ouput Anonymized Data (output.csv)</th>
    </tr>
    <tr>
        <td>
            <table>
                <tr>
                    <th>USER_ID</th>
                    <th>LOGIN_USERNAME</th>
                </tr>
                </tr>
                    <td>1</td>
                    <td>ben123</td>
                </tr>
                </tr>
                    <td>2</td>
                    <td>jen321</td>
                </tr>
                </tr>
                    <td>3</td>
                    <td>987jim</td>
                </tr>
            </table>
        </td>
        <td>
            <table>
                <tr>
                    <th>USER_ID</th>
                    <th>LOGIN_USERNAME</th>
                </tr>
                </tr>
                    <td>1</td>
                    <td>User321</td>
                </tr>
                </tr>
                    <td>2</td>
                    <td>User111</td>
                </tr>
                </tr>
                    <td>3</td>
                    <td>987jim</td>
                </tr>
            </table>
        </td>
    </tr>
</table>

The first two records `USER_ID = [1, 2]` both have `LOGIN_USERNAME` values that begin with a letter and end with a digit (these values match the pattern we defined: `(?<username_vals>^\w+\d+$)`) and so they are replaced with username values we defined in the `[Replacement_Values]` under the key `username_vals`.

The last record `USER_ID = 1 | LOGIN_USERNAME = 987jim` the `LOGIN_USERNAME` value does not match our custom regular expression (it starts with a digit not a letter) and so this data is not modified.