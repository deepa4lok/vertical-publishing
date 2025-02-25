from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = ["sale.order"]

    package = fields.Boolean(index=True, copy=False)
    package_description = fields.Char(copy=False)


class SaleOrderLine(models.Model):
    _inherit = ["sale.order.line"]

    package = fields.Boolean(
        related="order_id.package", string="Package", readonly=True, store=True
    )
