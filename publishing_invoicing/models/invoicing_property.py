from odoo import api, fields, models


class nsm_invoicing_property(models.Model):
    _name = "invoicing.property"

    name = fields.Char(string="Invoicing Property")
    group_by_advertiser = fields.Boolean(string="Group by Advertiser")
    active = fields.Boolean(default=True)

    # Correct invoice properties
    group_by_order = fields.Boolean(
        string="Group order lines with the same SO number on one invoice"
    )
    inv_package_deal = fields.Boolean(string="Invoice as package deal")
    inv_per_line_adv_print = fields.Boolean(
        string="Invoice print order lines on or after the selected date, invoice "
        "online order lines on or after startdate"
    )
    inv_per_line_after_online = fields.Boolean(string="Deprecated")
    inv_whole_order_at_once = fields.Boolean(
        string="Invoice all order lines on or after selected date "
    )
    inv_whole_order_afterwards = fields.Boolean(
        string="Invoice print order lines on or after issue date, invoice online "
        "order lines on or after start date"
    )
    inv_whole_order_enddate = fields.Boolean(
        string="Invoice print order lines on or after issue date, invoice online "
        "order lines on or after end date"
    )
    pay_in_terms = fields.Boolean(string="Invoice in terms")
    inv_per_line_after_print = fields.Boolean(
        string="Invoice per OrderLine afterwards print"
    )
    inv_per_line_adv_online = fields.Boolean(
        string="Invoice online order lines on or after the selected date, "
        "invoice print order lines on or after issue date"
    )
    inv_manually = fields.Boolean(string="Invoice Manually")
    regular_layout = fields.Boolean(string="Regular")
    default_property = fields.Boolean(string="Legacy")

    selected_invoicing_property_timing = fields.Selection(
        [
            (
                "inv_per_line_adv_print",
                "Invoice print order lines on or after the selected date, "
                "invoice online order lines on or after startdate",
            ),
            (
                "inv_whole_order_at_once",
                "Invoice all order lines on or after selected date",
            ),
            (
                "inv_whole_order_afterwards",
                "Invoice print order lines on or after issue date, "
                "invoice online order lines on or after start date",
            ),
            (
                "inv_whole_order_enddate",
                "Invoice print order lines on or after issue date, "
                "invoice online order lines on or after end date",
            ),
            (
                "inv_per_line_adv_online",
                "Invoice online order lines on or after the selected date, "
                "invoice print order lines on or after issue date",
            ),
            ("pay_in_terms", "Invoice in terms"),
            ("inv_manually", "Invoiced as specified in order"),
        ],
        "Timing",
        default="inv_per_line_adv_print",
    )

    selected_invoicing_property_layout = fields.Selection(
        [
            ("group_by_order", "One invoice per SO number"),
            ("inv_package_deal", "Invoice as package"),
            ("regular_layout", "Regular layout"),
        ],
        string="Layout",
        default="regular_layout",
    )

    def write(self, vals):
        """Convert a radio button value to a list of booleans (zero based)"""
        fields_timing = {
            "inv_per_line_adv_print": self.inv_per_line_adv_print,
            "inv_whole_order_at_once": self.inv_whole_order_at_once,
            "inv_whole_order_afterwards": self.inv_whole_order_afterwards,
            "inv_whole_order_enddate": self.inv_whole_order_enddate,
            "pay_in_terms": self.pay_in_terms,
            "inv_per_line_adv_online": self.inv_per_line_adv_online,
            "inv_manually": self.inv_manually,
        }
        fields_layout = {
            "group_by_order": self.group_by_order,
            "inv_package_deal": self.inv_package_deal,
            "regular_layout": self.regular_layout,
        }
        if "selected_invoicing_property_timing" in vals:
            for field_timing in fields_timing:
                if field_timing == str(vals["selected_invoicing_property_timing"]):
                    vals[field_timing] = True
                else:
                    vals[field_timing] = False
        if "selected_invoicing_property_layout" in vals:
            for field_layout in fields_layout:
                if field_layout == str(vals["selected_invoicing_property_layout"]):
                    vals[field_layout] = True
                else:
                    vals[field_layout] = False
        return super(nsm_invoicing_property, self).write(vals)

    @api.model
    def create(self, vals):
        vals[str(vals["selected_invoicing_property_timing"])] = True
        vals[str(vals["selected_invoicing_property_layout"])] = True
        return super(nsm_invoicing_property, self).create(vals)
