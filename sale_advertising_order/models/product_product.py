# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    height = fields.Integer(help="Height advertising format in mm", store=True)
    width = fields.Integer(help="Width advertising format in mm", store=True)
