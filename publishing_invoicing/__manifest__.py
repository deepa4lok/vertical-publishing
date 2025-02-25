{
    "name": "Publishing Invoicing",
    "summary": "Invoicing property feature added for invoicing",
    "author": "Magnus, Deepa (TOSC), The Open Source Company (TOSC)",
    "website": "https://github.com/OCA/l10n-netherlands",
    "category": "Sale",
    "license": "AGPL-3",
    "version": "16.0.6.0.0",
    # any module necessary for this one to work correctly
    "depends": ["sale_advertising_order_package", "sale_advertising_order_digital"],
    # FIXME: 'sale_advertising_order_invoice_customisation' -- does this app needed?
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/invoicing_property_view.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
    ],
    "demo": [
        "demo/invoicing_property.xml",
    ],
}
