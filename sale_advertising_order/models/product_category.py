# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = ["product.category"]

    date_type = fields.Selection(
        [
            ("validity", "Validity Date Range"),
            ("issue_date", "Issue Date"),
        ],
        help="Date Types for Advertising Products",
    )
    deadline_offset = fields.Integer("Hours offset from Issue Deadline", default=0)
    tag_ids = fields.Many2many(
        "account.analytic.tag",
        "product_category_tag_rel",
        "categ_id",
        "tag_id",
        string="Analytic Tags",
        copy=True,
    )
