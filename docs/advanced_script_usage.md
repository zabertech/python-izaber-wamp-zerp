Note: The type of field values to pass in vals for relationship fields is specific:

For a many2many field, a list of tuples is expected. Here is the list of tuple that are accepted, with the corresponding semantics

    (0, 0,  { values })    link to a new record that needs to be created with the given values dictionary
    (1, ID, { values })    update the linked record with id = ID (write *values* on it)
    (2, ID)                remove and delete the linked record with id = ID (calls unlink on ID, that will delete the object completely, and the link to it as well)
    (3, ID)                cut the link to the linked record with id = ID (delete the relationship between the two objects but does not delete the target object itself)
    (4, ID)                link to existing record with id = ID (adds a relationship)
    (5,)                    unlink all (like using (3,ID) for all linked records)
    (6, 0, [IDs])          replace the list of linked IDs (like using (5) then (4,ID) for each ID in the list of IDs)

    Example:
       [(6, 0, [8, 5, 6, 4])] sets the many2many to ids [8, 5, 6, 4]

For a one2many field, a lits of tuples is expected. Here is the list of tuple that are accepted, with the corresponding semantics

    (0, 0,  { values })    link to a new record that needs to be created with the given values dictionary
    (1, ID, { values })    update the linked record with id = ID (write *values* on it)
    (2, ID)                remove and delete the linked record with id = ID (calls unlink on ID, that will delete the object completely, and the link to it as well)

    Example:
       [(0, 0, {'field_name':field_value_record1, ...}), (0, 0, {'field_name':field_value_record2, ...})]

For a many2one field, simply use the ID of target record, which must already exist, or False to remove the link.

For a reference field, use a string with the model name, a comma, and the target object id (example: 'product.product, 5')

Original source: https://doc.odoo.com/6.0/developer/2_5_Objects_Fields_Methods/methods/#osv.osv.osv.write