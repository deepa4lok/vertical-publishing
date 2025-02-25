# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.depends("categ_id")
    def _compute_ads_products(self):
        """
        Compute the boolean for ads products.
        """
        ads_cat = self.env.ref("sale_advertising_order.advertising_category").id
        title_categ = self.env.ref(
            "sale_advertising_order.interface_portal_category"
        ).id
        for rec in self:
            parent_categ_ids = [
                int(p) for p in rec.categ_id.parent_path.split("/")[:-1]
            ]
            if ads_cat in parent_categ_ids or title_categ in parent_categ_ids:
                rec.is_ads_products = True
            else:
                rec.is_ads_products = False

    height = fields.Integer(help="Height advertising format in mm")
    width = fields.Integer(help="Width advertising format in mm")
    price_edit = fields.Boolean("Price Editable")
    is_ads_products = fields.Boolean("Is Ads Products?", compute=_compute_ads_products)

    @api.onchange("height", "width")
    def onchange_height_width(self):
        product_variant_ids = self.env["product.product"].search(
            [("product_tmpl_id", "=", self._origin.id)]
        )
        for variant in product_variant_ids:
            variant.write({"height": self.height})
            variant.write({"width": self.width})
