# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OrderLineAdvIssuesProducts(models.Model):
    _name = "sale.order.line.issues.products"
    _description = "Advertising Order Line Advertising Issues"
    _order = "order_line_id,sequence,id"

    @api.depends("price_unit", "qty")
    def _compute_price(self):
        for line in self:
            line.price = line.price_unit * line.qty

    @api.depends("adv_issue_id", "order_line_id.price_edit")
    def _compute_price_edit(self):
        for line in self:
            line.price_edit = False
            if line.order_line_id and line.order_line_id.price_edit:
                line.price_edit = True
                continue
            if line.adv_issue_id.parent_id.price_edit:
                line.price_edit = True

    sequence = fields.Integer(help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one(
        "sale.order.line", "Line", ondelete="cascade", index=True, required=True
    )
    adv_issue_id = fields.Many2one(
        "sale.advertising.issue",
        "Issue",
        ondelete="cascade",
        index=True,
        readonly=True,
        required=True,
    )
    product_attribute_value_id = fields.Many2one(
        related="adv_issue_id.parent_id.product_attribute_value_id",
        relation="sale.advertising.issue",
        string="Title",
        readonly=True,
    )
    product_id = fields.Many2one(
        "product.product", "Product", ondelete="cascade", index=True, readonly=True
    )
    price_unit = fields.Float(
        "Unit Price", required=True, digits="Product Price", default=0.0, readonly=True
    )
    price_edit = fields.Boolean(compute=_compute_price_edit, readonly=True)
    qty = fields.Float(related="order_line_id.product_uom_qty", readonly=True)
    price = fields.Float(
        compute="_compute_price",
        readonly=True,
        required=True,
        digits="Product Price",
        default=0.0,
    )
    page_reference = fields.Char("Reference of the Page", size=64)
    ad_number = fields.Char("External Reference", size=50)
    url_to_material = fields.Char("URL Material", size=64)
