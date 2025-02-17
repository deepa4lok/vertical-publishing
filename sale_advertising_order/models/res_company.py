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
    sao_show_discount_reason = fields.Boolean('Display discount reason to customer')
    sao_split_line_state = fields.Selection(selection=lambda self: self._sao_split_line_state_selection(), string='Sale order state for multiline split', default='draft')
    sao_split_lines_in_report = fields.Boolean('Display multi lines expanded in SO reports')
    sao_show_manual_approval_unconditionally = fields.Boolean('Display signature box on all sale reports')

    def _sao_split_line_state_selection(self):
        return self.env['sale.order']._fields['state'].selection
