from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    show_actual_unit_price = fields.Boolean(default=True)
