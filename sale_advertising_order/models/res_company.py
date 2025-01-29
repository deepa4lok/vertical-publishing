from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    show_actual_unit_price = fields.Boolean(default=True)
    sao_orderline_order_field_id = fields.Many2one(
        'ir.model.fields',
        string='Orderline sort order',
        default=lambda self: self.env.ref('sale.field_sale_order_line__sequence'),
        domain=[('model', '=', 'sale.order.line'), ('name', 'in', ('sequence', 'from_date', 'issue_date'))],
    )
