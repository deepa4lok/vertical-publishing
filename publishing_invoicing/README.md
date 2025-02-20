This module is an add-on for the advertising sales modules. It facilitates easier
invoicing, without the usage of filters for sale order lines which is the traditional
method. This module facilitates invoice properties. This module provides a new menu,
which one can use to create invoicing property objects per customer. In these objects,
one specifies how to invoice for this customer, e.g. per advertiser, per edition, per
period, online and print separated etc. When placing a new order, it is allowed to
choose another invoicing property when desired, although the default choice is the
invoice property belonging to the customer. The invoicing_property object has a one2many
relation with res.partner, and a one2many relation with sale.order.
