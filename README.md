# izaber.wamp.zerp

Base module that brings together most of the requirements to allow ZERP WAMP
connectivity within Zaber

## Installation

Install the module for your local version of python using the command below. If you have both python 2 and 3 installed then you might need to replace the `python` keyword with `python2`, `py -2`, `python3`, or `py -3` based on the python version you want to use the module for.

```
python -m pip install izaber-wamp-zerp
```

## Configuration

The module reads all of its settings from a globally defined configuration file located in the root directory of the user's computer. This configuration file is **required for proper operation** of the module.

- Create a file named `~/izaber.yaml` (i.e. in the home directory).
  - Linux: ``/home/yourusername/izaber.yaml``
  - MacOS: ``/Users/yourusername/izaber.yaml``
  - Windows: ``C:\Users\yourusername\izaber.yaml``

- Paste the following into the file to get started and connect to the `sandbox` database

  ```yaml
  default:
      wamp:
          connection:
              url: 'wss://nexus.izaber.com/ws'
              username: 'zaber'
              password: 'password_for_user'
              timeout: 10
          zerp:
              database: 'sandbox'
  ```
- Replace the username and password with your zerp user and a dashboard API key (If needed).
- More detailed information about defining the configuration files can be found [here](https://github.com/zabertech/python-izaber/blob/master/docs/tutorial.rst)

## Usage

### Initialization

To use the module in your script the module needs to be initialized and will need to make a WAMP connection to the server defined in your `~/izaber.yaml` file

```python
# Import the required parts of the module
from izaber import initialize
from izaber.wamp.zerp import zerp

...

# Inside the main part of your script

# Connect to Zerp over the WAMP bus
initialize('izaber-wamp')

# Use the 'zerp' object for the rest of your WAMP related code 
```

This will give you a `zerp` object that you can use to execute commands on the ZERP server you are connected to

### Getting a model

ZERP stores all its data in models. You will need to know the name of the model you wish to read from or write to.

Once you know the name of the model you are interested in, you can get a reference to it by using the following command in your script

```python
my_model = zerp.get_model('model.name')
```

### Model Methods

For each model, the following methods are available:
- `model.search(values)` - Search for data entries in the model whose values match your search terms
    - **Arguments**
        - values - *List of Tuples* - A list of tuples each tuple in the search domain needs to have 3 elements, in the form: `('field_name', 'operator', value)`.
            - field_name - *String* - The name of the field in the model whose values we are trying to search on
            - operator - *String* - A string with a valid comparison operator like `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `ilike`, `in`, `not in`, `child_of`, `parent_left`, and `parent_right`
            - value - A valid value to compare the fields values with in the model. Can be any basic variable type like string, int, float, etc.
    - **Returns**
        - A list of ids for each model item that matched the search terms
    - **Example**

        ```python
        ids = my_model.search([
            ('field_1', 'like', 'some_string'),
            ('field_2', '>=', 10)
        ])
        ```
- `model.read(ids, fields=None)` - Read the values of the fields defined
    - **Arguments**
        - ids - *List of ints* - Ids of items in the model whose values we want to read
        - fields - *List of strings* - Names of the fields that we want to read from the given module. Leave this field blank to read the values of all fields.
    - **Returns**
        - A list of dictionaries for each id you provided containing the values of the fields read
    - **Example**
    
        ```python
        values = my_model.read([1234], ['fields_1', 'field_2', 'field_3'])
        ```
- `write(ids, values)` - Write values to fields in the model for items with the given ids
    - **Arguments**
        - ids - *List of ints* - Ids of items in the model whose values we want to chane
        - values - *Dictionary* - Fields to change and the values to change them to. Writing to linked fields can also be achieved by defining a list of tuples for the one2many or many2many fields.
    - **Returns**
        - Always returns True
    - **Example**

        ```python
        my_model.write([1234], {
            'field_1': 'some_new_string',
            'field_2': 42,
            'field_5': 12.03,
            'field_6': [
                # Also update a linked item in some other model
                (1, 2345, {
                    'field_10': 0,
                    'field_11': 'A'
                }),
                (1, 2346, {
                    'field_10': 1,
                    'field_11': 'B'
                })
            ]
        })
        ```
- `create(values)`: Create new items in the model
    - **Arguments**
        - values - *Dictionary* - Field name and value combinations to create the item with. Creating linked fields can also be achieved by defining a list of tuples for the one2many or many2many fields.
    - **Returns**
        - id of the new item that is created in the model
    - **Example**

        ```python
        my_model.create({
            'field_1': 'some_new_string',
            'field_2': 42,
            'field_6': [
                # Create an item in some other model that will automatically be linked to this object
                (0, 0, {
                    'field_10': 0,
                    'field_11': 'A'
                }),
                (0, 0, {
                    'field_10': 1,
                    'field_11': 'B'
                }),
        })
        ```