# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    agency_discount = fields.Float("Agency Discount (%)", digits=(16, 2), default=0.0)
    is_ad_agency = fields.Boolean("Agency", default=False)

    @api.model
    def default_get(self, fields):
        """Function gets default values."""
        res = super().default_get(fields)
        res.update({"type": "contact"})
        return res
